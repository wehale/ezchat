"""kirbus — entry point."""

import argparse


def _cmd_decrypt_history(args) -> None:  # noqa: ANN001
    """Decrypt an encrypted history log and print to stdout."""
    import getpass
    from kirbus.home import get_home
    from kirbus.store.crypto_history import init_encryption, salt_path, is_encrypted_line, decrypt_line
    from kirbus.store.log import conv_path

    conv = args.decrypt_history
    if conv == "scratch":
        conv = "\x00scratch"

    if not salt_path(get_home()).exists():
        print("No encrypted history found (no .salt file)")
        return

    passphrase = getpass.getpass("History passphrase: ")
    if not init_encryption(passphrase, get_home()):
        print("Wrong passphrase.")
        return

    path = conv_path(conv)
    if not path.exists():
        print(f"No log found at {path}")
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        if is_encrypted_line(line):
            decrypted = decrypt_line(line)
            if decrypted:
                print(decrypted)
            else:
                print(line)  # can't decrypt, print raw
        else:
            print(line)


def _cmd_verify_log(args) -> None:  # noqa: ANN001
    """Verify Ed25519 signatures in a conversation log."""
    from kirbus.crypto.keys import load_or_create_identity
    from kirbus.store import verify_log, load_peers, get_pubkeys, conv_path

    conv = args.verify_log
    # Normalise common shorthands
    if conv == "scratch":
        conv = "\x00scratch"

    handle   = getattr(args, "handle", None) or "you"
    identity = load_or_create_identity(handle)
    pubkeys  = get_pubkeys(load_peers())
    pubkeys[identity.handle] = identity.public_key   # add self for scratch log

    results = verify_log(conv, pubkeys)
    path    = conv_path(conv)

    if not results:
        print(f"No log found at {path}")
        return

    ok_count   = sum(1 for _, ok, _, _ in results if ok)
    fail_count = len(results) - ok_count

    print(f"Log: {path}")
    print(f"  {ok_count}/{len(results)} signatures valid", end="")
    if fail_count:
        print(f"  ({fail_count} invalid/unsigned):")
        for lineno, ok, _sender, raw in results:
            if not ok:
                print(f"  line {lineno:>4}: {raw}")
    else:
        print("  ✓ all good")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kirbus",
        description="P2P end-to-end encrypted terminal chat",
    )

    # --- modes ---
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--test",
        action="store_true",
        help="Start in test mode with a built-in echo-bot peer (no network required)",
    )
    mode.add_argument(
        "--echo-server",
        action="store_true",
        help="Run as a headless echo agent (uses agent runner internally)",
    )
    mode.add_argument(
        "--agent",
        metavar="NAME_OR_SCRIPT",
        help="Run as a headless agent. Built-ins: 'games', 'echo'. Or pass a .py script path.",
    )
    mode.add_argument(
        "--bench",
        action="store_true",
        help="Run the latency benchmark suite",
    )

    # --- identity ---
    parser.add_argument("--handle", metavar="NAME", help="Your display name (default: you)")
    parser.add_argument("--theme",  metavar="NAME", help="UI theme to load on startup")

    # --- connection ---
    parser.add_argument("--connect", metavar="@HANDLE_OR_HOST:PORT",
                        help="Connect to a peer by @handle (requires --server) or host:port")
    parser.add_argument("--listen",  metavar="PORT", type=int,
                        help="Listen for incoming connections on PORT")
    parser.add_argument("--server",  metavar="URL",
                        help="kirbus-server URL (e.g. http://my-server.com:8000)")
    parser.add_argument("--registry", metavar="URL",
                        help="Registry URL (default: built-in). Use 'none' to disable.")
    parser.add_argument("--su", action="store_true",
                        help="Request superuser (admin) role (requires localhost)")
    parser.add_argument("--encrypt-history", action="store_true",
                        help="Enable passphrase encryption for chat history")
    parser.add_argument("--no-encrypt-history", action="store_true",
                        help="Disable history encryption and decrypt existing logs")

    # --- test mode options ---
    parser.add_argument("--echo-delay",  metavar="MS",   type=int, default=0, help="Simulated echo latency (ms)")
    parser.add_argument("--echo-script", metavar="FILE",           help="Scripted echo responses file")

    # --- bench options ---
    parser.add_argument("--target", metavar="HANDLE_OR_ADDR", help="Benchmark target peer")

    # --- state ---
    parser.add_argument(
        "--verify-log",
        metavar="CONV",
        help="Verify Ed25519 signatures in a conversation log (e.g. @alice, '#general', scratch)",
    )

    parser.add_argument(
        "--decrypt-history",
        metavar="CONV",
        help="Decrypt an encrypted history log to stdout (e.g. @alice, '#general', scratch)",
    )

    args = parser.parse_args()

    # Derive data directory from handle (e.g. ~/.kirbus-alice/)
    if getattr(args, "handle", None):
        from kirbus.home import set_handle
        set_handle(args.handle)

    if args.decrypt_history:
        _cmd_decrypt_history(args)
    elif args.verify_log:
        _cmd_verify_log(args)
    elif args.test:
        from kirbus.ui.app import run_test_mode
        run_test_mode(args)
    elif args.bench:
        from kirbus.bench.suite import run_suite
        run_suite(args)
    elif args.echo_server:
        from kirbus.agent.runner import run_builtin_echo
        run_builtin_echo(args)
    elif args.agent:
        from kirbus.agent.runner import run_agent
        run_agent(args)
    else:
        from kirbus.ui.app import run
        run(args)


if __name__ == "__main__":
    main()
