import ctypes
import errno
import socket

SCMP_ACT_ALLOW = 0x7FFF0000
SCMP_CMP_EQ = 4
PR_SET_NO_NEW_PRIVS = 38
PR_CAPBSET_DROP = 24


def _scmp_act_errno(err_no: int) -> int:
    return 0x00050000 | (err_no & 0x0000FFFF)


class ScmpArgCmp(ctypes.Structure):
    _fields_ = [
        ("arg", ctypes.c_uint),
        ("op", ctypes.c_int),
        ("datum_a", ctypes.c_uint64),
        ("datum_b", ctypes.c_uint64),
    ]


_BLOCKED_SOCKET_DOMAINS = (
    getattr(socket, "AF_UNIX", 1),
    getattr(socket, "AF_INET", 2),
    getattr(socket, "AF_INET6", 10),
    getattr(socket, "AF_NETLINK", 16),
    getattr(socket, "AF_PACKET", 17),
)

_BLOCKED_SYSCALLS = (
    "connect",
    "bind",
    "listen",
    "accept",
    "accept4",
    "sendto",
    "recvfrom",
    "sendmsg",
    "recvmsg",
    "ptrace",
    "mount",
    "umount2",
    "unshare",
    "setns",
    "io_uring_setup",
    "io_uring_enter",
    "io_uring_register",
    "keyctl",
    "add_key",
    "request_key",
    "bpf",
    "perf_event_open",
    "process_vm_readv",
    "process_vm_writev",
)


_LIBC = None
_LIBSECCOMP = None


def _get_libc():
    global _LIBC
    if _LIBC is None:
        _LIBC = ctypes.CDLL("libc.so.6", use_errno=True)
    return _LIBC


def _get_libseccomp():
    global _LIBSECCOMP
    if _LIBSECCOMP is None:
        lib = ctypes.CDLL("libseccomp.so.2", use_errno=True)
        lib.seccomp_init.argtypes = [ctypes.c_uint32]
        lib.seccomp_init.restype = ctypes.c_void_p
        lib.seccomp_release.argtypes = [ctypes.c_void_p]
        lib.seccomp_release.restype = None
        lib.seccomp_load.argtypes = [ctypes.c_void_p]
        lib.seccomp_load.restype = ctypes.c_int
        lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
        lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
        lib.seccomp_rule_add_array.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.POINTER(ScmpArgCmp),
        ]
        lib.seccomp_rule_add_array.restype = ctypes.c_int
        _LIBSECCOMP = lib
    return _LIBSECCOMP


try:
    _get_libc()
    _get_libseccomp()
except OSError:
    pass


def drop_bounding_caps_and_no_new_privs() -> None:
    libc = _get_libc()
    for cap in range(0, 45):
        libc.prctl(PR_CAPBSET_DROP, cap, 0, 0, 0)
    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        err = ctypes.get_errno()
        raise OSError(err, "PR_SET_NO_NEW_PRIVS failed")


def install_sandbox_seccomp() -> None:
    """Install seccomp-bpf filter in the sandbox child process using libseccomp.so.2."""
    lib = _get_libseccomp()

    ctx = lib.seccomp_init(SCMP_ACT_ALLOW)
    if not ctx:
        raise RuntimeError("seccomp_init failed")

    deny_eperm = _scmp_act_errno(errno.EPERM)
    try:
        for sock_call in (b"socket", b"socketpair"):
            nr = lib.seccomp_syscall_resolve_name(sock_call)
            if nr >= 0:
                for domain in _BLOCKED_SOCKET_DOMAINS:
                    cmp_arg = ScmpArgCmp(arg=0, op=SCMP_CMP_EQ, datum_a=domain, datum_b=0)
                    rc = lib.seccomp_rule_add_array(ctx, deny_eperm, nr, 1, ctypes.byref(cmp_arg))
                    if rc < 0:
                        raise RuntimeError(f"seccomp_rule_add_array failed for {sock_call!r} domain={domain}: {rc}")

        for name in _BLOCKED_SYSCALLS:
            nr = lib.seccomp_syscall_resolve_name(name.encode("ascii"))
            if nr >= 0:
                rc = lib.seccomp_rule_add_array(ctx, deny_eperm, nr, 0, None)
                if rc < 0:
                    raise RuntimeError(f"seccomp_rule_add_array failed for {name}: {rc}")

        rc = lib.seccomp_load(ctx)
        if rc < 0:
            raise RuntimeError(f"seccomp_load failed: {rc}")
    finally:
        lib.seccomp_release(ctx)
