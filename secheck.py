#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUntypedBaseClass=false, reportUnknownArgumentType=false
"""Module for checking kernel settings and system security."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import ClassVar

from textual.app import App  # type: ignore[import-unresolved]
from textual.containers import Vertical  # type: ignore[import-unresolved]
from textual.scroll_view import ScrollView  # type: ignore[import-unresolved]
from textual.widgets import Footer, Header, Static  # type: ignore[import-unresolved]

PASS_MIN_LEN_THRESHOLD: int = 12
USER_PROCESS_LIMIT_THRESHOLD: int = 10000
SECURE_PERMS_600: int = 600
SECURE_PERMS_644: int = 644
SYSTEMCTL_CMD: str = "/usr/bin/systemctl"


def read_kernel_setting(
    file_path: str,
    setting_name: str,
    enabled_message: str,
    disabled_message: str,
) -> str:
    """Read a kernel setting from a file and return a descriptive message.

    Args:
        file_path: Path to the kernel setting file.
        setting_name: Human-readable name of the setting.
        enabled_message: Message to return if the setting is enabled (1).
        disabled_message: Message to return if the setting is disabled (0).

    Returns:
        A string describing the state of the setting.

    """
    try:
        with Path(file_path).open() as file:
            setting_value = int(file.read().strip())
    except FileNotFoundError:
        return f"{setting_name} setting not found."
    except ValueError as e:
        return f"Error reading {setting_name}: {e}"
    else:
        if setting_value == 1:
            return enabled_message
        return disabled_message


def read_setting(
    file_path: str,
    expected_value: int,
    enabled_message: str,
    disabled_message: str,
) -> str:
    """Read a system setting and compare it against an expected value.

    Args:
        file_path: Path to the setting file.
        expected_value: The value representing an "enabled" or "secure" state.
        enabled_message: Message to return if the value matches the expected value.
        disabled_message: Message to return if the value does not match.

    Returns:
        A string describing whether the setting matches the expectation.

    """
    try:
        with Path(file_path).open() as file:
            value = int(file.read().strip())
    except FileNotFoundError:
        return f"{file_path} not found."
    except ValueError as e:
        return f"Error reading {file_path}: {e}"
    else:
        if value == expected_value:
            return enabled_message
        return disabled_message


class SecurityCheck(App[None]):
    """Textual application for running system security checks."""

    CSS_PATH: ClassVar[str] = "styles.css"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [("q", "quit", "Quit")]

    def __init__(self, **kwargs: object) -> None:
        """Initialize the SecurityCheck application.

        Args:
            **kwargs: Additional keyword arguments for the Textual App.

        """
        super().__init__(**kwargs)
        self.results: list[str] = []
        self.results_container: Vertical = Vertical()

    async def on_mount(self) -> None:
        """Mount the application widgets and start checks."""
        header = Header()
        footer = Footer()
        self.results_container = Vertical()

        await self.mount(header)
        await self.mount(ScrollView(self.results_container))
        await self.mount(footer)

        await self.run_all_checks()

    async def run_all_checks(self) -> None:
        """Execute all security check functions and display results."""
        if not self.check_root():
            await self.add_result("Please run as root.", status="failed")
            return

        await self.add_result("Starting security checks...", status="in_progress")

        checks = [
            (self.check_firewall, "Checking if a firewall is enabled..."),
            (self.check_password_policy, "Checking password policy..."),
            (self.check_ssh_config, "Checking SSH configuration..."),
            (self.check_auto_updates, "Checking for automatic updates..."),
            (self.check_sudoers, "Checking sudoers configuration..."),
            (self.check_suid_files, "Checking for SUID files..."),
            (self.check_common_services, "Checking common system services..."),
            (self.check_fork_bomb_protection, "Checking for fork bomb protection..."),
            (self.check_exploit_protections, "Checking for common exploit protections..."),
            (self.check_filesystem_permissions, "Checking filesystem permissions..."),
            (self.check_kernel_security, "Checking kernel security settings..."),
        ]

        for check_func, start_message in checks:
            await self.add_result(start_message, status="in_progress")

            try:
                result = check_func()
                if result:
                    await self.add_result(result, status="success")
            except (subprocess.SubprocessError, OSError) as e:
                await self.add_result(f"Error while performing check: {e}", status="failed")

    async def add_result(self, result: str, status: str = "success") -> None:
        """Add a result message to the display container.

        Args:
            result: The message to display.
            status: The status of the check ('success', 'failed', or 'in_progress').

        """
        color = "green" if status == "success" else "red" if status == "failed" else "yellow"
        self.results.append(result)
        await self.results_container.mount(Static(f"[{color}]{result}[/{color}]"))

    def check_root(self) -> bool:
        """Check if the script is running with root privileges.

        Returns:
            True if running as root, False otherwise.

        """
        return os.geteuid() == 0

    def check_firewall(self) -> str:
        """Check if ufw or firewalld is active.

        Returns:
            A string describing the firewall status.

        """
        try:
            ufw_status = subprocess.run(
                ["/usr/bin/ufw", "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            if ufw_status.stdout.find("Status: active") != -1:
                return "Firewall (ufw) is enabled."

            firewalld_status = subprocess.run(
                ["/usr/bin/systemctl", "is-active", "firewalld"],
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            return "No firewall software (ufw or firewalld) detected."
        except subprocess.SubprocessError as e:
            return f"Error checking firewall: {e}"
        else:
            if firewalld_status.returncode == 0:
                return "Firewall (firewalld) is enabled."
            return "Firewall is NOT enabled."

    def check_password_policy(self) -> str:
        """Verify the minimum password length in /etc/login.defs.

        Returns:
            A string describing the password policy status.

        """
        try:
            with Path("/etc/login.defs").open() as file:
                for line in file:
                    if line.startswith("PASS_MIN_LEN"):
                        min_length = int(line.split()[1])
                        if min_length >= PASS_MIN_LEN_THRESHOLD:
                            return f"Password minimum length is sufficient ({min_length} characters)."
                        return "Password min length is insufficient. Consider setting it to at least 12 characters."
                return "PASS_MIN_LEN setting not found in /etc/login.defs."
        except FileNotFoundError:
            return "Password policy file not found."
        except (ValueError, OSError) as e:
            return f"Error reading password policy: {e}"

    def check_ssh_config(self) -> str:
        """Check for secure SSH settings in /etc/ssh/sshd_config.

        Returns:
            A string summarizing SSH security settings.

        """
        ssh_config = "/etc/ssh/sshd_config"
        try:
            with Path(ssh_config).open() as file:
                content = file.read()
                result: list[str] = []
                if "PermitRootLogin no" in content:
                    result.append("Root login is disabled for SSH.")
                else:
                    result.append("Root login is ENABLED for SSH. It is recommended to disable it.")
                if "PasswordAuthentication no" in content:
                    result.append("Password authentication is disabled for SSH.")
                else:
                    result.append(
                        "Password authentication is ENABLED for SSH. Consider using key-based authentication.",
                    )
                return "\n".join(result)
        except FileNotFoundError:
            return "SSH configuration file not found."
        except OSError as e:
            return f"Error reading SSH configuration: {e}"

    def check_auto_updates(self) -> str:
        """Check if apt-daily-upgrade timer is active.

        Returns:
            A string describing the auto-update status.

        """
        try:
            status = subprocess.run(
                ["/usr/bin/systemctl", "list-timers"],
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.SubprocessError as e:
            return f"Error checking auto updates: {e}"
        else:
            if status.stdout.find("apt-daily-upgrade.timer") != -1:
                return "Automatic updates are enabled."
            return "Automatic updates are NOT enabled. Consider enabling unattended-upgrades."

    def check_sudoers(self) -> str:
        """Verify if the wheel group has sudo privileges.

        Returns:
            A string describing the sudoers status.

        """
        try:
            with Path("/etc/sudoers").open() as file:
                content = file.read()
                if "%wheel ALL=(ALL:ALL) ALL" in content:
                    return "Wheel group has sudo privileges configured properly."
                return "Wheel group does NOT have proper sudo privileges. Check your sudoers configuration."
        except FileNotFoundError:
            return "Sudoers configuration file not found."
        except OSError as e:
            return f"Error reading sudoers configuration: {e}"

    def check_suid_files(self) -> str:
        """Find all SUID files on the system.

        Returns:
            A list of found SUID files or a status message.

        """
        try:
            suid_files_res = subprocess.run(
                ["/usr/bin/find", "/", "-perm", "/4000", "-type", "f"],
                capture_output=True,
                text=True,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except subprocess.SubprocessError as e:
            return f"Error finding SUID files: {e}"
        else:
            suid_files = suid_files_res.stdout.strip()
            if suid_files:
                return f"List of SUID files found on the system:\n{suid_files}"
            return "No SUID files found."

    def check_common_services(self) -> str:
        """Check if insecure services like telnet are running.

        Returns:
            A summary of service status.

        """
        results = [
            self._check_telnet(),
            self._check_rsh(),
            self._check_rlogin(),
            self._check_rexec(),
        ]
        return "\n".join(results)

    def _check_telnet(self) -> str:
        """Check if telnet is running.

        Returns:
            A string describing the telnet status.

        """
        try:
            status = subprocess.run(["/usr/bin/systemctl", "is-active", "telnet"], capture_output=True, check=False)
        except subprocess.SubprocessError as e:
            return f"Error checking service telnet: {e}"
        else:
            if status.returncode == 0:
                return "Service telnet is running. It is recommended to disable it."
            return "Service telnet is not running."

    def _check_rsh(self) -> str:
        """Check if rsh is running.

        Returns:
            A string describing the rsh status.

        """
        try:
            status = subprocess.run(["/usr/bin/systemctl", "is-active", "rsh"], capture_output=True, check=False)
        except subprocess.SubprocessError as e:
            return f"Error checking service rsh: {e}"
        else:
            if status.returncode == 0:
                return "Service rsh is running. It is recommended to disable it."
            return "Service rsh is not running."

    def _check_rlogin(self) -> str:
        """Check if rlogin is running.

        Returns:
            A string describing the rlogin status.

        """
        try:
            status = subprocess.run(["/usr/bin/systemctl", "is-active", "rlogin"], capture_output=True, check=False)
        except subprocess.SubprocessError as e:
            return f"Error checking service rlogin: {e}"
        else:
            if status.returncode == 0:
                return "Service rlogin is running. It is recommended to disable it."
            return "Service rlogin is not running."

    def _check_rexec(self) -> str:
        """Check if rexec is running.

        Returns:
            A string describing the rexec status.

        """
        try:
            status = subprocess.run(["/usr/bin/systemctl", "is-active", "rexec"], capture_output=True, check=False)
        except subprocess.SubprocessError as e:
            return f"Error checking service rexec: {e}"
        else:
            if status.returncode == 0:
                return "Service rexec is running. It is recommended to disable it."
            return "Service rexec is not running."

    def check_fork_bomb_protection(self) -> str:
        """Check if the user process limit is set low enough.

        Returns:
            A string describing the process limit status.

        """
        try:
            limit_res = subprocess.run(
                ["/usr/bin/bash", "-c", "ulimit -u"],
                capture_output=True,
                text=True,
                check=False,
            )
            limit = int(limit_res.stdout.strip())
        except subprocess.SubprocessError as e:
            return f"Error checking fork bomb protection: {e}"
        except ValueError as e:
            return f"Error reading process limit: {e}"
        else:
            if limit < USER_PROCESS_LIMIT_THRESHOLD:
                return f"User process limit is set to {limit}. It is recommended to set a lower limit."
            return "User process limit is sufficient to prevent fork bombs."

    def check_exploit_protections(self) -> str:
        """Check for ASLR and source routing protection.

        Returns:
            A string summarizing exploit protection settings.

        """
        results: list[str] = []
        results.append(
            read_setting(
                "/proc/sys/kernel/randomize_va_space",
                2,
                "Address space layout randomization (ASLR) is enabled.",
                "ASLR is NOT fully enabled. Consider setting it to level 2 for maximum protection.",
            ),
        )

        results.append(
            read_setting(
                "/proc/sys/net/ipv4/conf/all/accept_source_route",
                0,
                "Source routing is disabled.",
                "Source routing is ENABLED. It is recommended to disable it.",
            ),
        )

        return "\n".join(results)

    def check_filesystem_permissions(self) -> str:
        """Check permissions of critical system files.

        Returns:
            A string summarizing file permission status.

        """
        critical_files = ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow"]
        results = [self._check_file_perms(f) for f in critical_files]
        return "\n".join(results)

    def _check_file_perms(self, file: str) -> str:
        """Check permissions of a single file.

        Args:
            file: The path to the file to check.

        Returns:
            A string describing the file permission status.

        """
        try:
            perms = int(oct(Path(file).stat().st_mode)[-3:])
        except FileNotFoundError:
            return f"{file} not found."
        except OSError as e:
            return f"Error checking permissions for {file}: {e}"
        else:
            if file in ["/etc/shadow", "/etc/gshadow"]:
                if perms <= SECURE_PERMS_600:
                    return f"Permissions for {file} are secure ({perms})."
                return f"Permissions for {file} are insecure ({perms}). Consider setting it to 600 or less."
            if perms <= SECURE_PERMS_644:
                return f"Permissions for {file} are secure ({perms})."
            return f"Permissions for {file} are insecure ({perms}). Consider setting it to 644 or less."

    def check_kernel_security(self) -> str:
        """Check kernel pointer and dmesg restrictions.

        Returns:
            A string summarizing kernel security settings.

        """
        results: list[str] = []
        results.append(
            read_kernel_setting(
                "/proc/sys/kernel/kptr_restrict",
                "Kernel pointer restriction",
                "Kernel pointer restrictions are enabled.",
                "Kernel pointer restrictions are NOT enabled. Consider enabling them for better security.",
            ),
        )

        results.append(
            read_kernel_setting(
                "/proc/sys/kernel/dmesg_restrict",
                "Kernel dmesg restriction",
                "Kernel dmesg restrictions are enabled.",
                "Kernel dmesg restrictions are NOT enabled. Consider enabling them for better security.",
            ),
        )

        results.append(
            read_kernel_setting(
                "/proc/sys/kernel/sysrq",
                "Magic SysRq key",
                "Magic SysRq key is disabled.",
                "Magic SysRq key is ENABLED. It is recommended to disable it.",
            ),
        )

        return "\n".join(results)


if __name__ == "__main__":
    SecurityCheck().run()
