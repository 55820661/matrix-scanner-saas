import io

import paramiko


class SSHCommandError(Exception):
    pass


class ParamikoSSHClient:
    def __init__(self, hostname, port, username, auth_method, secret, timeout=10):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.auth_method = auth_method
        self.secret = secret
        self.timeout = timeout
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def __enter__(self):
        kwargs = {
            "hostname": self.hostname,
            "port": self.port,
            "username": self.username,
            "timeout": self.timeout,
            "banner_timeout": self.timeout,
            "auth_timeout": self.timeout,
        }
        if self.auth_method == "password":
            kwargs["password"] = self.secret
        else:
            kwargs["pkey"] = self._private_key_from_string(self.secret)
        self.client.connect(**kwargs)
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.client.close()

    def run(self, command, timeout=30):
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return {
            "exit_code": exit_code,
            "stdout": stdout.read().decode("utf-8", errors="replace"),
            "stderr": stderr.read().decode("utf-8", errors="replace"),
        }

    def put_bytes(self, remote_path, data):
        with self.client.open_sftp() as sftp:
            with sftp.file(remote_path, "wb") as remote_file:
                remote_file.write(data)

    @staticmethod
    def _private_key_from_string(secret):
        last_error = None
        for key_cls in (paramiko.RSAKey, paramiko.ECDSAKey, paramiko.Ed25519Key):
            try:
                return key_cls.from_private_key(io.StringIO(secret))
            except paramiko.SSHException as exc:
                last_error = exc
        raise last_error or paramiko.SSHException("Unsupported private key.")
