#!/usr/bin/env python3
"""Stress tests for bin/git-ssh-sign, using ssh(1) itself as the oracle for
key order.

Run with `python3 tests/test_git_ssh_sign.py`. Needs ssh, sshd, ssh-agent,
ssh-keyscan, git and pgrep; the tests start their own sshd on a free local
port, which rejects every key, and their own ssh-agents. They never touch the
caller's ssh-agent or keys: every child gets an explicit SSH_AUTH_SOCK, or
none. GSS_WRAPPER selects another copy of the wrapper to test."""

import base64
import concurrent.futures
import fcntl
import hashlib
import importlib.machinery
import importlib.util
import os
import pty
import re
import select
import shutil
import signal
import socket
import socketserver
import subprocess
import sys
import tempfile
import termios
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WRAPPER = os.environ.get(
    "GSS_WRAPPER", os.path.join(os.path.dirname(HERE), "bin", "git-ssh-sign")
)
DEVNULL = subprocess.DEVNULL
PIPE = subprocess.PIPE

_loader = importlib.machinery.SourceFileLoader("git_ssh_sign", WRAPPER)
_spec = importlib.util.spec_from_loader("git_ssh_sign", _loader)
assert _spec is not None
W = importlib.util.module_from_spec(_spec)
_loader.exec_module(W)

ROOT = tempfile.mkdtemp(prefix="gss-test.")
TMP = os.path.join(ROOT, "tmp")  # TMPDIR for the wrapper: must end empty
K = os.path.join(ROOT, "keys")
NON_UTF8_A = os.path.join(K, os.fsdecode(b"non-utf8-\xff"), "A")
BASE_ENV = {k: v for k, v in os.environ.items() if not k.startswith("SSH_")}
BASE_ENV["TMPDIR"] = TMP


def run(argv, env=None, **kw):
    kw.setdefault("stdout", PIPE)
    kw.setdefault("stderr", PIPE)
    kw.setdefault("stdin", DEVNULL)
    kw.setdefault("timeout", 60)
    return subprocess.run(argv, env=env or BASE_ENV, start_new_session=True, **kw)


def children(pid):
    out = subprocess.run(["pgrep", "-P", str(pid)], stdout=PIPE).stdout
    return [int(x) for x in out.split()]


def fp(blob):
    return "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip(
        "="
    )


def describe(blob):
    """(type, fingerprint) as ssh prints them: a certificate's fingerprint
    is that of the key it certifies."""
    kind = W.key_type(blob)[0]
    if kind in W.CERT_KEY_FIELDS:
        name, pos = W.read_string(blob, 0)
        start = W.read_string(blob, pos)[1]  # skip the nonce
        end = start
        for _ in range(W.CERT_KEY_FIELDS[kind]):
            end = W.read_string(blob, end)[1]
        plain = name.replace(
            b"-cert-v01@openssh.com",
            b"@openssh.com" if name.startswith(b"sk-") else b"",
        )
        blob = len(plain).to_bytes(4, "big") + plain + blob[start:end]
    return kind.upper(), fp(blob)


def pub_fp(path):
    with open(path) as f:
        return describe(base64.b64decode(f.read().split()[1]))


def keygen(path, *args):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    run(
        ["ssh-keygen", "-q", "-N", "", "-C", os.path.basename(path), "-f", path]
        + list(args),
        check=True,
    )


def copy_key(src, dst, pub=True, priv=True):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if priv:
        shutil.copy(src, dst)
        os.chmod(dst, 0o600)
    if pub:
        shutil.copy(src + ".pub", dst + ".pub")


def slurp(path, mode="rb"):
    with open(path, mode) as f:
        return f.read()


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


SSHD_PORT = ""  # set by start_sshd()
SSHD = []  # the running sshd, for tearDownModule()


def start_sshd():
    """A throwaway sshd on a free local port that rejects every key."""
    global SSHD_PORT
    sshd = shutil.which("sshd", path=os.environ["PATH"] + ":/usr/sbin:/usr/local/sbin")
    if sshd is None:
        raise RuntimeError("the tests need sshd")
    d = os.path.join(ROOT, "sshd")
    keygen(f"{d}/host_key", "-t", "ed25519")
    write(f"{d}/authorized_keys", b"")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        SSHD_PORT = str(s.getsockname()[1])
    config = f"""
        Port {SSHD_PORT}
        ListenAddress 127.0.0.1
        HostKey {d}/host_key
        PidFile none
        UsePAM no
        StrictModes no
        AuthorizedKeysFile {d}/authorized_keys
        PasswordAuthentication no
        KbdInteractiveAuthentication no
        PerSourcePenalties no
        MaxStartups 1000
        MaxAuthTries 50
    """
    write(
        f"{d}/sshd_config", "\n".join(x.strip() for x in config.splitlines()).encode()
    )
    SSHD.append(
        subprocess.Popen(
            [sshd, "-D", "-f", f"{d}/sshd_config"],
            stdout=DEVNULL,
            stderr=DEVNULL,
            start_new_session=True,
        )
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", int(SSHD_PORT))) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError("sshd did not start")


def setUpModule():
    os.makedirs(TMP)
    start_sshd()
    keygen(f"{K}/A", "-t", "ed25519")
    keygen(f"{K}/B", "-t", "ed25519")
    keygen(f"{K}/C", "-t", "ecdsa")
    keygen(f"{K}/R", "-t", "rsa", "-b", "2048")
    keygen(f"{K}/CA", "-t", "ed25519")
    keygen(f"{K}/E", "-t", "ed25519")
    run(["ssh-keygen", "-q", "-p", "-P", "", "-N", "pw", "-f", f"{K}/E"], check=True)
    copy_key(f"{K}/E", f"{K}/E-plain")  # same key, unencrypted, for ssh-add
    run(
        ["ssh-keygen", "-q", "-p", "-P", "pw", "-N", "", "-f", f"{K}/E-plain"],
        check=True,
    )
    copy_key(f"{K}/A", f"{K}/privonly/A", pub=False)
    copy_key(f"{K}/A", f"{K}/pubonly/A", priv=False)
    copy_key(f"{K}/E", f"{K}/encnopub/E", pub=False)
    copy_key(f"{K}/A", f"{K}/with space/A")
    copy_key(f"{K}/A", NON_UTF8_A)
    copy_key(f"{K}/A", f"{K}/perm/A")
    os.chmod(f"{K}/perm/A", 0o644)  # ssh refuses to use it
    # Restricted agent keys are only listed to ssh for permitted hosts, so
    # permit the test sshd: the agent still refuses unbound git signatures.
    scan = run(
        ["ssh-keyscan", "-t", "ed25519", "-p", SSHD_PORT, "127.0.0.1"], check=True
    )
    # ssh-keyscan also prints a "# host:port banner" comment to stdout.
    line = next(x for x in scan.stdout.splitlines() if not x.startswith(b"#"))
    host_key = line.split(b" ", 1)[1] + b"\n"
    write(f"{K}/known_hosts", b"127.0.0.1 " + host_key)
    keygen(f"{K}/pem/R", "-t", "rsa", "-b", "2048", "-m", "PEM")
    os.unlink(f"{K}/pem/R.pub")
    for kind, flag in (("certuser", []), ("certhost", ["-h"])):
        copy_key(f"{K}/A", f"{K}/{kind}/A")
        run(
            ["ssh-keygen", "-q", "-s", f"{K}/CA", "-I", kind, "-n", "test,localhost"]
            + flag
            + [f"{K}/{kind}/A.pub"],
            check=True,
        )
    os.makedirs(f"{K}/adir")
    make_weird_files()


def make_weird_files():
    a = slurp(f"{K}/A.pub").rstrip(b"\n")
    b = slurp(f"{K}/B.pub").rstrip(b"\n")
    r = slurp(f"{K}/R.pub").rstrip(b"\n")
    a_type, a_b64, _ = a.split(b" ")
    b_type, b_b64, _ = b.split(b" ")
    r_b64 = r.split(b" ")[1]
    priv = slurp(f"{K}/A")
    w = f"{K}/weird"
    cases = {
        "comments": b"# c\n\n#x\n" + a + b"\n",
        "leading_ws": b" \t " + a + b"\n",
        "crlf_nocomment": a_type + b" " + a_b64 + b"\r\n",
        "tabs": a_type + b"\t\t" + a_b64 + b"\tcomment\n",
        "wrong_type_then_b": b"ecdsa-sha2-nistp256 " + a_b64 + b"\n" + b + b"\n",
        "unknown_type_then_b": b"ssh-foo " + a_b64 + b"\n" + b + b"\n",
        "bad_padding_then_b": a_type
        + b" "
        + a_b64.rstrip(b"=")[:-1]
        + b"\n"
        + b
        + b"\n",
        "sig_name_rsa": b"rsa-sha2-256 " + r_b64 + b" x\n",
        "type_only_then_b": a_type + b"\n" + a_type + b" \n" + b + b"\n",
        "nul_in_line": a_type + b"\0 junk\n" + b + b"\n",
        "nul_first": b"\0" + a + b"\n" + b + b"\n",
        "options_prefix_then_b": b'from="x" ' + a + b"\n" + b + b"\n",
        "empty": b"",
        "begin_then_key": b"-----BEGIN FOO\n" + a + b"\n",
        "space_begin_then_key": b" -----BEGIN FOO\n" + a + b"\n",
        "vtab_in_base64": a_type + b" " + a_b64[:10] + b"\x0b" + a_b64[10:] + b"\n",
        "cr_in_base64": a_type + b" " + a_b64[:10] + b"\r" + a_b64[10:] + b"\n",
        "no_newline": a,
        "garbage": os.urandom(300),
        "b_blob_a_comment": b_type + b" " + b_b64 + b" " + a + b"\n",
        "priv_crlf": priv.replace(b"\n", b"\r\n"),
        "priv_trailing_junk": priv + b"junk\n" + b,
        "priv_leading_blank": b"\n" + priv,
        "priv_no_end": priv.split(b"-----END")[0],
        "priv_spaces": priv.replace(b"\n", b" \n", 3),
    }
    for name, data in cases.items():
        write(f"{w}/{name}", data)
    # Private key that cannot hold the key, with a .pub that can or cannot.
    write(f"{w}/sshprivfile", b"SSH PRIVATE KEY FILE")
    write(f"{w}/sshprivfile.pub", b + b"\n")
    write(f"{w}/priv_with_bad_pub", priv)
    write(f"{w}/priv_with_bad_pub.pub", b"garbage\n")
    write(f"{w}/priv_with_b_pub", priv)
    write(f"{w}/priv_with_b_pub.pub", b + b"\n")


def tearDownModule():
    for sshd in SSHD:
        sshd.terminate()
        sshd.wait()
    leftovers = os.listdir(TMP)
    shutil.rmtree(ROOT, ignore_errors=True)
    assert not leftovers, f"temporary files left behind: {leftovers}"


class Agent:
    """A throwaway ssh-agent. Keys in `deny` need confirmation, which the
    agent's askpass (/bin/false) always refuses."""

    def __init__(self, keys=(), deny=(), restrict=(), askpass="/bin/false"):
        # Short path: sun_path holds about 108 bytes.
        self.dir = tempfile.mkdtemp(prefix="gssa.")
        self.sock = os.path.join(self.dir, "sock")
        env = dict(
            BASE_ENV, SSH_ASKPASS=askpass, SSH_ASKPASS_REQUIRE="force", DISPLAY=":0"
        )
        self.proc = subprocess.Popen(
            ["ssh-agent", "-D", "-a", self.sock],
            env=env,
            stdout=DEVNULL,
            stderr=DEVNULL,
            start_new_session=True,
        )
        for _ in range(200):
            if os.path.exists(self.sock):
                break
            time.sleep(0.01)
        try:
            for key in keys:
                flags = ["-c"] if key in deny else []
                if key in restrict:  # usable only for ssh to 127.0.0.1
                    flags += ["-H", f"{K}/known_hosts", "-h", "127.0.0.1"]
                run(["ssh-add", "-q"] + flags + [key], env=self.env, check=True)
        except BaseException:
            self.close()
            raise

    @property
    def env(self):
        return dict(BASE_ENV, SSH_AUTH_SOCK=self.sock)

    def close(self):
        self.proc.terminate()
        self.proc.wait()
        shutil.rmtree(self.dir, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class NoAgent:
    env = BASE_ENV

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


class DeadAgent(NoAgent):
    """SSH_AUTH_SOCK names a socket nobody listens on."""

    env = dict(BASE_ENV, SSH_AUTH_SOCK=os.path.join(ROOT, "no-agent"))


SSH_AGENT_FAILURE = 5
SSH2_AGENTC_REQUEST_IDENTITIES = 11
SSH2_AGENT_IDENTITIES_ANSWER = 12
SSH2_AGENTC_SIGN_REQUEST = 13


def ssh_string(data):
    return len(data).to_bytes(4, "big") + data


def recv_exact(conn, size):
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


class HangUpAgent:
    """An agent that lists its keys but, asked to sign, waits and then drops
    the connection without answering, as 1Password does when its approval
    prompt times out (ssh-keygen: "communication with agent failed")."""

    def __init__(self, keys, delay):
        blobs = [base64.b64decode(slurp(f"{key}.pub").split()[1]) for key in keys]
        identities = (
            bytes([SSH2_AGENT_IDENTITIES_ANSWER])
            + len(blobs).to_bytes(4, "big")
            + b"".join(ssh_string(b) + ssh_string(b"hang-up") for b in blobs)
        )

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                while True:
                    header = recv_exact(self.request, 4)
                    if header is None:
                        return
                    body = recv_exact(self.request, int.from_bytes(header, "big"))
                    if not body:
                        return
                    if body[0] == SSH2_AGENTC_SIGN_REQUEST:
                        time.sleep(delay)
                        return  # hang up without a reply
                    if body[0] == SSH2_AGENTC_REQUEST_IDENTITIES:
                        reply = identities
                    else:
                        reply = bytes([SSH_AGENT_FAILURE])
                    self.request.sendall(ssh_string(reply))

        # Short path: sun_path holds about 108 bytes.
        self.dir = tempfile.mkdtemp(prefix="gssa.")
        self.sock = os.path.join(self.dir, "sock")
        self.server = socketserver.ThreadingUnixStreamServer(self.sock, Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def env(self):
        return dict(BASE_ENV, SSH_AUTH_SOCK=self.sock)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.dir, ignore_errors=True)


def empty_agent():
    return Agent()


def ssh_order(identity_file, env):
    """ssh's own key order: its "Will attempt key" lines, as
    (fingerprint or None, from agent) pairs."""
    p = run(
        [
            "ssh",
            "-v",
            "-F",
            "/dev/null",
            "-p",
            SSHD_PORT,
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "GlobalKnownHostsFile=/dev/null",
            "-o",
            "IdentitiesOnly=no",
            "-o",
            f'IdentityFile="{identity_file}"',
            "127.0.0.1",
            "true",
        ],
        env=env,
    )
    err = p.stderr.decode(errors="replace")
    assert "Authenticated to" not in err and "Will attempt key" in err, err
    order = []
    for line in err.splitlines():
        if "Will attempt key: " in line:
            m = re.search(r" (\S+) (SHA256:[A-Za-z0-9+/]+)", line)
            order.append((m.groups() if m else None, line.endswith(" agent")))
    return order


def wrapper_order(identity_file, env):
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(env)
    try:
        idents = W.candidates(identity_file)
    finally:
        os.environ.clear()
        os.environ.update(saved)
    return [(describe(i.blob) if i.blob else None, i.key_file is None) for i in idents]


def check_novalidate(sig, data):
    p = run(
        ["ssh-keygen", "-Y", "check-novalidate", "-n", "git", "-s", sig],
        input=data,
        stdin=None,
    )
    m = re.search(rb"with (\S+) key (SHA256:[A-Za-z0-9+/]+)", p.stdout)
    if p.returncode or not m:
        return None
    return tuple(g.decode() for g in m.groups())


def git_sign(
    key,
    env,
    literal=False,
    args=None,
    files=1,
    data=b"payload\n",
    stdin_mode=False,
    python=sys.executable,
):
    """Run the wrapper the way git does. Returns (status, signer per file,
    stderr)."""
    work = tempfile.mkdtemp(dir=ROOT, prefix="sign.")
    paths = []
    for n in range(files):
        paths.append(os.path.join(work, f".git_signing_buffer_tmp{n}"))
        write(paths[-1], data)
    if literal:
        key_file = os.path.join(work, ".git_signing_key_tmpXYZ")
        with open(key) as f:
            write(key_file, f.read().strip().encode())
        key = key_file
    argv = args if args is not None else ["-Y", "sign", "-n", "git", "-f", key]
    if literal:
        argv = argv + ["-U"]
    if stdin_mode is True:
        operands = []
    elif stdin_mode == "-":
        operands = ["-"]
    else:
        operands = paths
    p = run(
        [python, WRAPPER] + argv + operands,
        env=env,
        input=data if stdin_mode else None,
        stdin=None if stdin_mode else DEVNULL,
    )
    if stdin_mode:
        write(paths[0] + ".sig", p.stdout)
    signers = [
        check_novalidate(path + ".sig", data)
        if os.path.exists(path + ".sig") and os.path.getsize(path + ".sig")
        else None
        for path in paths
    ]
    shutil.rmtree(work)
    return p.returncode, signers, p.stderr.decode(errors="replace")


IDENTITY_FILES = [
    "A",
    "privonly/A",
    "pubonly/A",
    "missing",
    "E",
    "encnopub/E",
    "pem/R",
    "certuser/A",
    "certhost/A",
    "A.pub",
    "with space/A",
    "adir",
    "B",
    "perm/A",
    os.path.relpath(NON_UTF8_A, K),
]
AGENTS = {
    "none": lambda: NoAgent(),
    "dead": lambda: DeadAgent(),
    "restricted B": lambda: Agent([f"{K}/B"], restrict=[f"{K}/B"]),
    "empty": empty_agent,
    "B": lambda: Agent([f"{K}/B"]),
    "A": lambda: Agent([f"{K}/A"]),
    "B,A": lambda: Agent([f"{K}/B", f"{K}/A"]),
    "A,B": lambda: Agent([f"{K}/A", f"{K}/B"]),
    "B,C,R": lambda: Agent([f"{K}/B", f"{K}/C", f"{K}/R"]),
    "certuser": lambda: Agent([f"{K}/certuser/A"]),
    "B,certuser": lambda: Agent([f"{K}/B", f"{K}/certuser/A"]),
    "certhost,B": lambda: Agent([f"{K}/certhost/A", f"{K}/B"]),
    "E": lambda: Agent([f"{K}/E-plain"]),
    "B,E": lambda: Agent([f"{K}/B", f"{K}/E-plain"]),
}


class KeyOrderMatchesSsh(unittest.TestCase):
    """candidates() must equal ssh's "Will attempt key" order."""

    def test_key_types_match_installed_ssh(self):
        def query(kind):
            out = run(["ssh", "-Q", kind], check=True).stdout
            return set(out.split())

        self.assertEqual(set(W.KEY_TYPES), query("key-sig"))
        certs = {n for n, (kind, _) in W.KEY_TYPES.items() if kind in W.CERT_KEY_FIELDS}
        self.assertEqual(query("key-cert"), certs & query("key"))
        self.assertEqual(
            {kind for kind, _ in W.KEY_TYPES.values() if kind.endswith("-cert")},
            set(W.CERT_KEY_FIELDS),
        )

    def test_agents_by_identity_files(self):
        for agent_name, make in AGENTS.items():
            with make() as agent:
                for ident in IDENTITY_FILES:
                    path = f"{K}/{ident}"
                    with self.subTest(agent=agent_name, identity=ident):
                        self.assertEqual(
                            wrapper_order(path, agent.env), ssh_order(path, agent.env)
                        )

    def test_public_key_parsing(self):
        weird = sorted(os.listdir(f"{K}/weird"))
        self.assertGreater(len(weird), 25)
        with Agent([f"{K}/B"]) as agent:
            for env_name, env in (("none", BASE_ENV), ("B", agent.env)):
                for name in weird:
                    if name.endswith(".pub"):
                        continue
                    path = f"{K}/weird/{name}"
                    with self.subTest(agent=env_name, file=name):
                        self.assertEqual(wrapper_order(path, env), ssh_order(path, env))


class Signing(unittest.TestCase):
    def expect(self, key, agent, signer, **kw):
        status, signers, err = git_sign(key, agent.env, **kw)
        if signer is None:
            self.assertNotEqual(status, 0, err)
            self.assertEqual(set(signers), {None}, err)
        else:
            self.assertEqual(status, 0, err)
            self.assertEqual(signers, [pub_fp(signer)] * len(signers), err)
        return err

    def test_file_only(self):
        self.expect(f"{K}/A", NoAgent(), f"{K}/A.pub")
        with empty_agent() as a:
            self.expect(f"{K}/A", a, f"{K}/A.pub")

    def test_missing_file_without_agent_reports_ssh_keygen_error(self):
        err = self.expect(f"{K}/missing", NoAgent(), None)
        self.assertIn("Couldn't load public key", err)

    def test_agent_key_preferred_over_file(self):
        with Agent([f"{K}/B"]) as a:
            self.expect(f"{K}/A", a, f"{K}/B.pub")
            self.expect(f"{K}/missing", a, f"{K}/B.pub")

    def test_agent_copy_of_file_key_comes_first(self):
        with Agent([f"{K}/B", f"{K}/A"]) as a:
            self.expect(f"{K}/A", a, f"{K}/A.pub")
        with Agent([f"{K}/A", f"{K}/B"]) as a:
            self.expect(f"{K}/A", a, f"{K}/A.pub")

    def test_falls_back_after_agent_refuses(self):
        with Agent([f"{K}/B"], deny=[f"{K}/B"]) as a:
            err = self.expect(f"{K}/A", a, f"{K}/A.pub")
            self.assertIn("agent refused operation", err)
        with Agent([f"{K}/B", f"{K}/C"], deny=[f"{K}/B"]) as a:
            self.expect(f"{K}/A", a, f"{K}/C.pub")

    def test_refused_agent_copy_is_not_retried_from_file(self):
        # ssh moves an IdentityFile held by the agent out of the file list.
        with Agent([f"{K}/A"], deny=[f"{K}/A"]) as a:
            self.expect(f"{K}/A", a, None)
        with Agent([f"{K}/A", f"{K}/B"], deny=[f"{K}/A"]) as a:
            self.expect(f"{K}/A", a, f"{K}/B.pub")

    def test_encrypted_file(self):
        self.expect(f"{K}/E", NoAgent(), None)  # no tty: no passphrase
        with Agent([f"{K}/B"]) as a:
            self.expect(f"{K}/E", a, f"{K}/B.pub")
            self.expect(f"{K}/encnopub/E", a, f"{K}/B.pub")
        with Agent([f"{K}/E-plain"]) as a:
            self.expect(f"{K}/E", a, f"{K}/E.pub")
            self.expect(f"{K}/encnopub/E", a, f"{K}/E.pub")

    def test_public_key_only(self):
        self.expect(f"{K}/pubonly/A", NoAgent(), None)
        with Agent([f"{K}/A"]) as a:
            self.expect(f"{K}/pubonly/A", a, f"{K}/A.pub")
        with Agent([f"{K}/B"]) as a:
            self.expect(f"{K}/pubonly/A", a, f"{K}/B.pub")
        self.expect(f"{K}/A.pub", NoAgent(), f"{K}/A.pub")

    def test_literal_key(self):
        err = self.expect(f"{K}/A.pub", NoAgent(), None, literal=True)
        self.assertIn("Couldn't get agent socket", err)
        with Agent([f"{K}/A"]) as a:
            self.expect(f"{K}/A.pub", a, f"{K}/A.pub", literal=True)
        with Agent([f"{K}/B", f"{K}/A"]) as a:
            self.expect(f"{K}/A.pub", a, f"{K}/A.pub", literal=True)
        with Agent([f"{K}/B"]) as a:
            self.expect(f"{K}/A.pub", a, f"{K}/B.pub", literal=True)
        with Agent([f"{K}/B"], deny=[f"{K}/B"]) as a:
            err = self.expect(f"{K}/A.pub", a, None, literal=True)
            # git's -U (the key is in the agent) still applies to its key.
            self.assertIn("Couldn't find key in agent", err)

    def test_certificates_sign_with_first_ssh_identity(self):
        for agent_name in ("none", "certuser", "B,certuser", "certhost,B"):
            for ident in ("certuser/A", "certhost/A"):
                subtest = self.subTest(agent=agent_name, identity=ident)
                with subtest, AGENTS[agent_name]() as a:
                    first = ssh_order(f"{K}/{ident}", a.env)[0][0]
                    status, signers, err = git_sign(f"{K}/{ident}", a.env)
                    self.assertEqual(status, 0, err)
                    self.assertEqual(signers, [first], err)

    def test_path_with_space(self):
        self.expect(f"{K}/with space/A", NoAgent(), f"{K}/A.pub")
        with Agent([f"{K}/B"]) as a:
            self.expect(f"{K}/with space/A", a, f"{K}/B.pub")

    def test_other_requests_get_ssh_keygens_own_key(self):
        # Only git's form gets key selection; anything else goes to
        # ssh-keygen, which uses the -f key A because the agent lacks it.
        A = f"{K}/A"
        for agent_keys, deny in (([f"{K}/B"], []), ([f"{K}/B"], [f"{K}/B"])):
            with Agent(agent_keys, deny=deny) as a:
                for kw in (
                    dict(stdin_mode=True),
                    dict(stdin_mode="-"),
                    dict(files=3),
                    dict(args=["-q", "-Y", "sign", "-n", "git", "-f", A]),
                    dict(args=["-g", "-Y", "sign", "-n", "git", "-f", A]),
                    dict(
                        args=[
                            "-Y",
                            "sign",
                            "-n",
                            "git",
                            "-O",
                            "hashalg=sha256",
                            "-f",
                            A,
                        ]
                    ),
                ):
                    with self.subTest(
                        deny=bool(deny), **{k: str(v) for k, v in kw.items()}
                    ):
                        self.expect(A, a, f"{K}/A.pub", **kw)

    def test_git_request_forms(self):
        A = f"{K}/A"
        forms = [
            ["-Ysign", "-ngit", "-f" + A],
            ["-Y", "signature", "-n", "git", "-f", A],
            ["-f", f"{K}/missing", "-Y", "sign", "-n", "git", "-f", A],
            ["-Y", "sign", "-n", "git", "-f", A, "--"],
            ["-U", "-Y", "sign", "-n", "git", "-f", A],
        ]
        for argv in forms:
            with self.subTest(argv=argv), Agent([f"{K}/B"]) as a:
                self.expect(A, a, f"{K}/B.pub", args=argv)

    def test_host_certificate_key_is_refused(self):
        host_cert = f"{K}/certhost/A-cert.pub"
        err = self.expect(host_cert, NoAgent(), None)
        self.assertIn("is a certificate that is not a user certificate", err)
        with Agent([f"{K}/B"]) as a:
            self.expect(host_cert, a, f"{K}/B.pub")

    def test_parallel(self):
        def one(env, expected):
            status, signers, err = git_sign(f"{K}/A", env)
            return status == 0 and signers == [pub_fp(expected)]

        with Agent([f"{K}/B"]) as a, Agent([f"{K}/B"], deny=[f"{K}/B"]) as d:
            with concurrent.futures.ThreadPoolExecutor(16) as pool:
                jobs = [pool.submit(one, a.env, f"{K}/B.pub") for _ in range(40)]
                jobs += [pool.submit(one, d.env, f"{K}/A.pub") for _ in range(20)]
                jobs += [pool.submit(one, BASE_ENV, f"{K}/A.pub") for _ in range(20)]
                self.assertTrue(all(j.result() for j in jobs))

    def test_restricted_agent_key_falls_back(self):
        with Agent([f"{K}/B"], restrict=[f"{K}/B"]) as a:
            err = self.expect(f"{K}/A", a, f"{K}/A.pub")
            self.assertIn("agent refused operation", err)

    def test_agent_hanging_up_falls_back(self):
        delay = 0.5
        with HangUpAgent([f"{K}/B"], delay) as a:
            start = time.monotonic()
            err = self.expect(f"{K}/A", a, f"{K}/A.pub")
            self.assertGreaterEqual(time.monotonic() - start, delay)
            self.assertIn("communication with agent failed", err)
            err = self.expect(f"{K}/missing", a, None)
            self.assertIn("communication with agent failed", err)

    def test_dead_agent_socket_means_no_agent_keys(self):
        self.expect(f"{K}/A", DeadAgent(), f"{K}/A.pub")
        self.expect(f"{K}/missing", DeadAgent(), None)

    def test_key_file_with_open_permissions_is_not_used(self):
        err = self.expect(f"{K}/perm/A", NoAgent(), None)
        self.assertIn("are too open", err)
        with Agent([f"{K}/B"]) as a:
            self.expect(f"{K}/perm/A", a, f"{K}/B.pub")
        with Agent([f"{K}/B"], deny=[f"{K}/B"]) as a:
            err = self.expect(f"{K}/perm/A", a, None)
            self.assertIn("agent refused operation", err)
            self.assertIn("are too open", err)

    def test_path_not_valid_utf8(self):
        self.expect(NON_UTF8_A, NoAgent(), f"{K}/A.pub")
        with Agent([f"{K}/B"]) as a:
            self.expect(NON_UTF8_A, a, f"{K}/B.pub")
        with Agent([f"{K}/B", f"{K}/A"]) as a:
            self.expect(NON_UTF8_A, a, f"{K}/A.pub")

    def test_missing_tools_are_reported(self):
        bin_dir = tempfile.mkdtemp(dir=ROOT, prefix="bin.")
        keygen = shutil.which("ssh-keygen")
        assert keygen is not None
        os.symlink(keygen, os.path.join(bin_dir, "ssh-keygen"))
        work = tempfile.mkdtemp(dir=ROOT)
        write(os.path.join(work, "m"), b"x")
        for path, missing, argv in (
            (bin_dir, "ssh-add", ["-Y", "sign", "-n", "git", "-f", f"{K}/A"]),
            (work, "ssh-keygen", ["-lf", f"{K}/A.pub"]),
        ):
            with self.subTest(missing=missing):
                p = run(
                    [sys.executable, WRAPPER] + argv + [os.path.join(work, "m")],
                    env=dict(BASE_ENV, PATH=path),
                )
                self.assertEqual(p.returncode, 1)
                self.assertIn(
                    f"git-ssh-sign: [Errno 2] No such file or directory: '{missing}'",
                    p.stderr.decode(),
                )

    def start_blocked_sign(self, agent):
        """A wrapper whose first ssh-keygen blocks on "Overwrite (y/n)?"
        because the .sig file exists."""
        work = tempfile.mkdtemp(dir=ROOT)
        buf = os.path.join(work, "buf")
        write(buf, b"x")
        write(buf + ".sig", b"old")
        p = subprocess.Popen(
            [sys.executable, WRAPPER, "-Y", "sign", "-n", "git", "-f", f"{K}/A", buf],
            env=agent.env,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            start_new_session=True,
        )
        deadline = time.time() + 20
        while time.time() < deadline and not children(p.pid):
            time.sleep(0.01)
        time.sleep(0.3)
        self.assertTrue(children(p.pid))
        return p

    def assert_gone(self, p):
        for _ in range(500):  # ssh-keygen must not outlive the wrapper
            try:
                os.killpg(p.pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.01)
        else:
            self.fail("ssh-keygen outlived the wrapper")
        self.assertEqual(os.listdir(TMP), [])

    def test_signal_to_wrapper_is_passed_to_ssh_keygen(self):
        for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            with self.subTest(signal=signum.name), Agent([f"{K}/B"]) as a:
                p = self.start_blocked_sign(a)
                p.send_signal(signum)  # the wrapper only
                _, err = p.communicate(timeout=20)
                self.assertEqual(p.returncode, -signum, err)
                self.assert_gone(p)

    def test_signal_at_passphrase_prompt_restores_terminal(self):
        """The forwarded signal lets ssh-keygen turn echo back on; killing
        it outright would leave the terminal without echo."""
        master, tty = pty.openpty()
        work = tempfile.mkdtemp(dir=ROOT)
        buf = os.path.join(work, "buf")
        write(buf, b"x")
        try:
            with Agent([f"{K}/B"], deny=[f"{K}/B"]) as a:
                p = subprocess.Popen(
                    [sys.executable, WRAPPER, "-Y", "sign", "-n", "git"]
                    + ["-f", f"{K}/E", buf],
                    env=a.env,
                    stdin=tty,
                    stdout=tty,
                    stderr=tty,
                    start_new_session=True,
                    preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0),
                )
                shown = b""
                deadline = time.time() + 20
                while b"passphrase" not in shown and time.time() < deadline:
                    if select.select([master], [], [], 0.2)[0]:
                        shown += os.read(master, 4096)
                self.assertIn(b"passphrase", shown)
                self.assertFalse(termios.tcgetattr(tty)[3] & termios.ECHO)
                p.send_signal(signal.SIGTERM)
                p.wait(timeout=20)
                self.assertEqual(p.returncode, -signal.SIGTERM)
                self.assertTrue(termios.tcgetattr(tty)[3] & termios.ECHO)
        finally:
            os.close(master)
            os.close(tty)
        self.assertEqual(os.listdir(TMP), [])

    def test_interrupt_of_process_group(self):
        with Agent([f"{K}/B"]) as a:
            p = self.start_blocked_sign(a)
            os.killpg(p.pid, signal.SIGINT)  # as Ctrl-C does
            _, err = p.communicate(timeout=20)
            self.assertEqual(p.returncode, -signal.SIGINT, err)
            self.assert_gone(p)

    def test_ssh_keygen_killed_by_sigkill(self):
        with Agent([f"{K}/B"]) as a:
            p = self.start_blocked_sign(a)
            for pid in children(p.pid):
                os.kill(pid, signal.SIGKILL)
            _, err = p.communicate(timeout=20)
            self.assertEqual(p.returncode, -signal.SIGKILL, err)
            self.assertNotIn(b"Traceback", err)
            self.assert_gone(p)


class PassThrough(unittest.TestCase):
    """Anything but a sign request must behave exactly like ssh-keygen."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(dir=ROOT)
        cls.data = b"payload\n"
        cls.msg = os.path.join(cls.work, "msg")
        write(cls.msg, cls.data)
        run(
            ["ssh-keygen", "-q", "-Y", "sign", "-n", "git", "-f", f"{K}/A", cls.msg],
            check=True,
        )
        cls.sig = cls.msg + ".sig"
        cls.allowed = os.path.join(cls.work, "allowed")
        with open(f"{K}/A.pub") as f:
            write(cls.allowed, b"me@example.com " + f.read().encode())
        cls.readonly = os.path.join(cls.work, "readonly")
        write(os.path.join(cls.readonly, "msg"), cls.data)
        os.chmod(cls.readonly, 0o555)

    @classmethod
    def tearDownClass(cls):
        os.chmod(cls.readonly, 0o755)

    def assert_same(self, argv, prefix=(), **kw):
        want = run(list(prefix) + ["ssh-keygen"] + argv, **kw)
        got = run(list(prefix) + [sys.executable, WRAPPER] + argv, **kw)
        self.assertEqual(
            (got.returncode, got.stdout, got.stderr),
            (want.returncode, want.stdout, want.stderr),
        )

    def test_reader_closing_early_ends_ssh_keygen_with_sigpipe(self):
        keys = os.path.join(self.work, "many.pub")
        write(keys, slurp(f"{K}/A.pub") * 5000)
        statuses = []
        for prefix in ([], [sys.executable, WRAPPER]):
            argv = prefix + ["-lf", keys] if prefix else ["ssh-keygen", "-lf", keys]
            p = subprocess.Popen(argv, stdout=PIPE, stderr=DEVNULL, env=BASE_ENV)
            assert p.stdout is not None
            p.stdout.read(1)
            p.stdout.close()
            statuses.append(p.wait(timeout=20))
        self.assertEqual(statuses, [-signal.SIGPIPE, -signal.SIGPIPE])

    def test_closed_stdin(self):
        # ssh-keygen's sanitise_stdfd() opens /dev/null for a closed stdin.
        closed = ["sh", "-c", 'exec "$0" "$@" 0<&-']
        argv = ["-Y", "sign", "-n", "git", "-f", f"{K}/A"]
        with Agent([f"{K}/B"]) as a:
            self.assert_same(argv, prefix=closed, env=a.env)

    def test_locale_reaches_ssh_keygen_unchanged(self):
        """Run the wrapper through its #! line, as git does, in the C
        locale: Python must not coerce LC_CTYPE for ssh-keygen (PEP 538)."""
        pub = os.path.join(self.work, "u.pub")
        write(pub, slurp(f"{K}/A.pub").rsplit(b" ", 1)[0] + " h\u00e9llo\n".encode())
        with open(WRAPPER, "rb") as f:
            interpreter, arg = f.readline()[2:].decode().strip().split(" ", 1)
        env = {"PATH": BASE_ENV["PATH"], "LANG": "C", "TMPDIR": TMP}
        want = run(["ssh-keygen", "-lf", pub], env=env)
        got = run([interpreter, arg, WRAPPER, "-lf", pub], env=env)
        self.assertIn(b"h\\303\\251llo", want.stdout)  # escaped in C
        self.assertEqual(
            (got.returncode, got.stdout, got.stderr),
            (want.returncode, want.stdout, want.stderr),
        )

    def test_identical_results(self):
        A, sig, allowed = f"{K}/A", self.sig, self.allowed
        cases = [
            (["-Y", "find-principals", "-f", allowed, "-s", sig, ""], None),
            (
                [
                    "-Y",
                    "find-principals",
                    "-f",
                    allowed,
                    "-s",
                    sig,
                    "-Overify-time=20260101000000",
                ],
                None,
            ),
            (
                [
                    "-Y",
                    "verify",
                    "-n",
                    "git",
                    "-f",
                    allowed,
                    "-I",
                    "me@example.com",
                    "-s",
                    sig,
                    "",
                ],
                self.data,
            ),
            (
                [
                    "-Y",
                    "verify",
                    "-n",
                    "git",
                    "-f",
                    allowed,
                    "-I",
                    "nobody",
                    "-s",
                    sig,
                    "",
                ],
                self.data,
            ),
            (
                [
                    "-Y",
                    "verify",
                    "-n",
                    "git",
                    "-f",
                    allowed,
                    "-I",
                    "me@example.com",
                    "-s",
                    sig,
                ],
                b"tampered\n",
            ),
            (["-Y", "check-novalidate", "-n", "git", "-s", sig, ""], self.data),
            (["-lf", A], None),
            (["-lf", "-"], slurp(f"{K}/B.pub")),
            (["-lf", f"{K}/missing"], None),
            (["-Y", "bogus"], None),
            (["-%"], None),
            (["-Y"], None),
            (["-Y", "sign", "-f", A, self.msg], None),
            (["-Y", "sign", "-n", "git", self.msg], None),
            (["-Y", "sign", "-n", "", "-f", A, self.msg], None),
            (["-Y", "sign", "-n", "git", "-f", A, "-", self.msg], None),
            (["-Y", "sign", self.msg, "-n", "git", "-f", A], None),
            # Signing requests not in git's form, or that cannot succeed.
            (["-Y", "sign", "-n", "git", "-f", A], self.data),
            (["-Y", "sign", "-n", "git", "-f", A, "-"], self.data),
            (["-Y", "sign", "-n", "git", "-q", "-f", A, self.msg], None),
            (
                ["-Y", "sign", "-n", "git", "-O", "hashalg=bogus", "-f", A, self.msg],
                None,
            ),
            (["-Y", "sign", "-n", "git", "-f", A, self.work + "/nonexistent"], None),
            (["-Y", "sign", "-n", "git", "-f", A, self.readonly + "/msg"], None),
        ]
        with Agent([f"{K}/B"]) as a:
            for env in (BASE_ENV, a.env):
                for argv, data in cases:
                    with self.subTest(argv=argv, agent=env is a.env):
                        kw = dict(
                            env=env,
                            input=data,
                            stdin=None if data is not None else DEVNULL,
                        )
                        want = run(["ssh-keygen"] + argv, **kw)
                        got = run([sys.executable, WRAPPER] + argv, **kw)
                        self.assertEqual(
                            (got.returncode, got.stdout, got.stderr),
                            (want.returncode, want.stdout, want.stderr),
                        )


@unittest.skipUnless(
    os.access(WRAPPER, os.X_OK), "git needs an executable gpg.ssh.program"
)
class GitEndToEnd(unittest.TestCase):
    def commit(self, env, signing_key):
        repo = tempfile.mkdtemp(dir=ROOT, prefix="repo.")
        git = [
            "git",
            "-C",
            repo,
            "-c",
            "gpg.format=ssh",
            "-c",
            f"gpg.ssh.program={WRAPPER}",
            "-c",
            f"user.signingKey={signing_key}",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "-c",
            f"gpg.ssh.allowedSignersFile={self.allowed}",
        ]
        env = dict(env, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
        run(["git", "init", "-q", repo], env=env, check=True)
        p = run(git + ["commit", "-q", "-S", "--allow-empty", "-m", "t"], env=env)
        if p.returncode:
            return None, p.stderr.decode()
        out = run(git + ["log", "-1", "--format=%G? %GK"], env=env)
        verify = run(git + ["verify-commit", "HEAD"], env=env)
        self.assertEqual(verify.returncode, 0, verify.stderr)
        return out.stdout.decode().split(), None

    @classmethod
    def setUpClass(cls):
        cls.allowed = os.path.join(ROOT, "git-allowed")
        lines = b""
        for k in "ABCE":
            with open(f"{K}/{k}.pub", "rb") as f:
                lines += b"t@example.com " + f.read()
        write(cls.allowed, lines)

    def test_commits(self):
        with Agent([f"{K}/B"]) as b, Agent([f"{K}/B", f"{K}/A"]) as ba:
            for env, key, want in (
                (BASE_ENV, f"{K}/A", "A"),
                (b.env, f"{K}/A", "B"),
                (ba.env, f"{K}/A", "A"),
                (b.env, "~/does-not-exist", "B"),
                (ba.env, "key::" + slurp(f"{K}/A.pub", "r").strip(), "A"),
                (b.env, slurp(f"{K}/A.pub", "r").strip(), "B"),
            ):
                with self.subTest(key=key[:30], want=want):
                    got, err = self.commit(env, key)
                    self.assertIsNone(err, err)
                    self.assertEqual(got, ["G", pub_fp(f"{K}/{want}.pub")[1]])


if __name__ == "__main__":
    print(f"python {sys.version.split()[0]}", file=sys.stderr)
    unittest.main(verbosity=2)
