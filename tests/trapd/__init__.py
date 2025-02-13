import asyncio


async def send_trap_externally(*args: str):
    """Uses the snmptrap command line program to send a trap to the local trap receiver test instance on port 1162.

    :param args: The arguments to pass to the snmptrap command line program, see `man snmptrap` for details on the
                 rather esoteric syntax.
    """
    args = " ".join(args)
    proc = await asyncio.create_subprocess_shell(f"snmptrap -v 2c -c public localhost:1162 '' {args}")
    await proc.communicate()
    assert proc.returncode == 0, "snmptrap command exited with error"
