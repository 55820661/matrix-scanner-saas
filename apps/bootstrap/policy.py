from dataclasses import dataclass


class BootstrapPolicyError(Exception):
    pass


@dataclass(frozen=True)
class CommandTemplate:
    key: str
    command: str
    requires_confirmation: bool = False


APT_PACKAGES = ("python3", "python3-venv", "python3-pip")
DNF_PACKAGES = ("python3", "python3-pip")
YUM_PACKAGES = ("python3", "python3-pip")

COMMAND_TEMPLATES = {
    "remote_os_probe": CommandTemplate("remote_os_probe", "cat /etc/os-release"),
    "systemd_detector": CommandTemplate("systemd_detector", "test -d /run/systemd/system && command -v systemctl"),
    "privilege_check": CommandTemplate("privilege_check", 'test "$(id -u)" = "0" || sudo -n true'),
    "package_manager_detector": CommandTemplate(
        "package_manager_detector",
        "command -v apt-get || command -v dnf || command -v yum",
    ),
    "python_runtime_detector": CommandTemplate("python_runtime_detector", "command -v python3"),
    "apt_package_install": CommandTemplate(
        "apt_package_install",
        "sudo -n apt-get update && sudo -n apt-get install -y python3 python3-venv python3-pip",
        requires_confirmation=True,
    ),
    "dnf_package_install": CommandTemplate(
        "dnf_package_install",
        "sudo -n dnf install -y python3 python3-pip",
        requires_confirmation=True,
    ),
    "yum_package_install": CommandTemplate(
        "yum_package_install",
        "sudo -n yum install -y python3 python3-pip",
        requires_confirmation=True,
    ),
    "bootstrap_directory_prepare": CommandTemplate(
        "bootstrap_directory_prepare",
        "sudo -n mkdir -p /opt/matrix_scanner/logs /opt/matrix_scanner/data && sudo -n chown -R root:root /opt/matrix_scanner && sudo -n chmod 755 /opt/matrix_scanner",
    ),
    "scanner_archive_extract": CommandTemplate(
        "scanner_archive_extract",
        "sudo -n tar -xzf /tmp/matrix_scanner_runtime.tar.gz -C /opt/matrix_scanner",
    ),
    "scanner_config_install": CommandTemplate(
        "scanner_config_install",
        "sudo -n mv /tmp/matrix_scanner_config.json /opt/matrix_scanner/config.json && sudo -n chmod 600 /opt/matrix_scanner/config.json",
    ),
    "systemd_service_install": CommandTemplate(
        "systemd_service_install",
        "sudo -n mv /tmp/matrix-scanner-agent.service /etc/systemd/system/matrix-scanner-agent.service && sudo -n systemctl daemon-reload",
    ),
    "systemd_service_start": CommandTemplate(
        "systemd_service_start",
        "sudo -n systemctl enable --now matrix-scanner-agent.service",
    ),
}


PACKAGE_MANAGER_TEMPLATE = {
    "apt": "apt_package_install",
    "dnf": "dnf_package_install",
    "yum": "yum_package_install",
}


def require_template(template_key):
    try:
        return COMMAND_TEMPLATES[template_key]
    except KeyError as exc:
        raise BootstrapPolicyError("Unknown bootstrap command template.") from exc


def render_command(template_key, *, confirmed=False):
    template = require_template(template_key)
    if template.requires_confirmation and not confirmed:
        raise BootstrapPolicyError("Package installation requires explicit confirmation.")
    return template.command


def package_install_template(package_manager):
    try:
        return PACKAGE_MANAGER_TEMPLATE[package_manager]
    except KeyError as exc:
        raise BootstrapPolicyError("Unsupported package manager.") from exc


def reject_raw_command(command):
    if command not in {template.command for template in COMMAND_TEMPLATES.values()}:
        raise BootstrapPolicyError("Raw shell commands are not allowed in bootstrap.")
    return True
