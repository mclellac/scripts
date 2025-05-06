#!/usr/bin/env python
import os
import subprocess
from typing import List

from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static
from textual.scroll_view import ScrollView


def read_kernel_setting(
    file_path: str, setting_name: str, enabled_message: str, disabled_message: str
) -> str:
    try:
        with open(file_path, "r") as file:
            setting_value = int(file.read().strip())
            if setting_value == 1:
                return enabled_message
            else:
                return disabled_message
    except FileNotFoundError:
        return f"{setting_name} setting not found."
    except ValueError as e:
        return f"Error reading {setting_name}: {e}"


def read_setting(
    file_path: str, expected_value: int, enabled_message: str, disabled_message: str
) -> str:
    try:
        with open(file_path, "r") as file:
            value = int(file.read().strip())
            if value == expected_value:
                return enabled_message
            else:
                return disabled_message
    except FileNotFoundError:
        return f"{file_path} not found."
    except ValueError as e:
        return f"Error reading {file_path}: {e}"


class SecurityCheck(App):
    CSS_PATH = "styles.css"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results = []

    async def on_mount(self) -> None:
        header = Header()
        footer = Footer()
        self.results_container = Vertical()

        await self.mount(header)
        await self.mount(ScrollView(self.results_container))
        await self.mount(footer)

        await self.run_all_checks()

    async def run_all_checks(self):
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
            (
                self.check_exploit_protections,
                "Checking for common exploit protections...",
            ),
            (self.check_filesystem_permissions, "Checking filesystem permissions..."),
            (self.check_kernel_security, "Checking kernel security settings..."),
        ]

        for check_func, start_message in checks:
            await self.add_result(start_message, status="in_progress")

            try:
                result = check_func()
                if result:
                    await self.add_result(result, status="success")
            except Exception as e:
                await self.add_result(
                    f"Error while performing check: {e}", status="failed"
                )

    async def add_result(self, result: str, status: str = "success"):
        color = (
            "green"
            if status == "success"
            else "red" if status == "failed" else "yellow"
        )
        self.results.append(result)
        await self.results_container.mount(Static(f"[{color}]{result}[/{color}]"))

    def check_root(self) -> bool:
        return os.geteuid() == 0

    def check_firewall(self) -> str:
        try:
            if (
                subprocess.run(
                    ["ufw", "status"], stdout=subprocess.PIPE, text=True
                ).stdout.find("Status: active")
                != -1
            ):
                return "Firewall (ufw) is enabled."
            elif (
                subprocess.run(
                    ["systemctl", "is-active", "firewalld"], stdout=subprocess.PIPE
                ).returncode
                == 0
            ):
                return "Firewall (firewalld) is enabled."
            else:
                return "Firewall is NOT enabled."
        except FileNotFoundError:
            return "No firewall software (ufw or firewalld) detected."
        except subprocess.SubprocessError as e:
            return f"Error checking firewall: {e}"

    def check_password_policy(self) -> str:
        try:
            with open("/etc/login.defs", "r") as file:
                for line in file:
                    if line.startswith("PASS_MIN_LEN"):
                        min_length = int(line.split()[1])
                        if min_length >= 12:
                            return f"Password minimum length is sufficient ({min_length} characters)."
                        else:
                            return "Password min length is insufficient. Consider setting it to at least 12 characters."
                return "PASS_MIN_LEN setting not found in /etc/login.defs."
        except FileNotFoundError:
            return "Password policy file not found."
        except ValueError as e:
            return f"Error reading password policy: {e}"

    def check_ssh_config(self) -> str:
        ssh_config = "/etc/ssh/sshd_config"
        try:
            with open(ssh_config, "r") as file:
                content = file.read()
                result = []
                if "PermitRootLogin no" in content:
                    result.append("Root login is disabled for SSH.")
                else:
                    result.append(
                        "Root login is ENABLED for SSH. It is recommended to disable it."
                    )
                if "PasswordAuthentication no" in content:
                    result.append("Password authentication is disabled for SSH.")
                else:
                    result.append(
                        "Password authentication is ENABLED for SSH. Consider using key-based authentication."
                    )
                return "\n".join(result)
        except FileNotFoundError:
            return "SSH configuration file not found."
        except Exception as e:
            return f"Error reading SSH configuration: {e}"

    def check_auto_updates(self) -> str:
        try:
            if (
                subprocess.run(
                    ["systemctl", "list-timers"], stdout=subprocess.PIPE, text=True
                ).stdout.find("apt-daily-upgrade.timer")
                != -1
            ):
                return "Automatic updates are enabled."
            else:
                return "Automatic updates are NOT enabled. Consider enabling unattended-upgrades."
        except subprocess.SubprocessError as e:
            return f"Error checking auto updates: {e}"

    def check_sudoers(self) -> str:
        try:
            with open("/etc/sudoers", "r") as file:
                content = file.read()
                if "%wheel ALL=(ALL:ALL) ALL" in content:
                    return "Wheel group has sudo privileges configured properly."
                else:
                    return "Wheel group does NOT have proper sudo privileges. Check your sudoers configuration."
        except FileNotFoundError:
            return "Sudoers configuration file not found."
        except Exception as e:
            return f"Error reading sudoers configuration: {e}"

    def check_suid_files(self) -> str:
        try:
            suid_files = subprocess.run(
                ["find", "/", "-perm", "/4000", "-type", "f"],
                stdout=subprocess.PIPE,
                text=True,
                stderr=subprocess.DEVNULL,
            ).stdout.strip()
            if suid_files:
                return f"List of SUID files found on the system:\n{suid_files}"
            else:
                return "No SUID files found."
        except subprocess.SubprocessError as e:
            return f"Error finding SUID files: {e}"

    def check_common_services(self) -> str:
        services = ["telnet", "rsh", "rlogin", "rexec"]
        results = []
        for service in services:
            try:
                if (
                    subprocess.run(
                        ["systemctl", "is-active", service], stdout=subprocess.PIPE
                    ).returncode
                    == 0
                ):
                    results.append(
                        f"Service {service} is running. It is recommended to disable it."
                    )
                else:
                    results.append(f"Service {service} is not running.")
            except subprocess.SubprocessError as e:
                results.append(f"Error checking service {service}: {e}")
        return "\n".join(results)

    def check_fork_bomb_protection(self) -> str:
        try:
            limit = int(
                subprocess.run(
                    ["bash", "-c", "ulimit -u"], stdout=subprocess.PIPE, text=True
                ).stdout.strip()
            )
            if limit < 10000:
                return f"User process limit is set to {limit}. It is recommended to set a lower limit to prevent fork bombs."
            else:
                return "User process limit is sufficient to prevent fork bombs."
        except subprocess.SubprocessError as e:
            return f"Error checking fork bomb protection: {e}"
        except ValueError as e:
            return f"Error reading process limit: {e}"

    def check_exploit_protections(self) -> str:
        results = []
        results.append(
            read_setting(
                "/proc/sys/kernel/randomize_va_space",
                2,
                "Address space layout randomization (ASLR) is enabled.",
                "ASLR is NOT fully enabled. Consider setting it to level 2 for maximum protection.",
            )
        )

        results.append(
            read_setting(
                "/proc/sys/net/ipv4/conf/all/accept_source_route",
                0,
                "Source routing is disabled.",
                "Source routing is ENABLED. It is recommended to disable it.",
            )
        )

        return "\n".join(results)

    def check_filesystem_permissions(self) -> str:
        critical_files = ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow"]
        results = []
        for file in critical_files:
            try:
                perms = int(oct(os.stat(file).st_mode)[-3:])
                if file in ["/etc/shadow", "/etc/gshadow"]:
                    if perms <= 600:
                        results.append(f"Permissions for {file} are secure ({perms}).")
                    else:
                        results.append(
                            f"Permissions for {file} are insecure ({perms}). Consider setting it to 600 or less."
                        )
                else:
                    if perms <= 644:
                        results.append(f"Permissions for {file} are secure ({perms}).")
                    else:
                        results.append(
                            f"Permissions for {file} are insecure ({perms}). Consider setting it to 644 or less."
                        )
            except FileNotFoundError:
                results.append(f"{file} not found.")
            except Exception as e:
                results.append(f"Error checking permissions for {file}: {e}")
        return "\n".join(results)

    def check_kernel_security(self) -> str:
        results = []
        results.append(
            read_kernel_setting(
                "/proc/sys/kernel/kptr_restrict",
                "Kernel pointer restriction",
                "Kernel pointer restrictions are enabled.",
                "Kernel pointer restrictions are NOT enabled. Consider enabling them for better security.",
            )
        )

        results.append(
            read_kernel_setting(
                "/proc/sys/kernel/dmesg_restrict",
                "Kernel dmesg restriction",
                "Kernel dmesg restrictions are enabled.",
                "Kernel dmesg restrictions are NOT enabled. Consider enabling them for better security.",
            )
        )

        results.append(
            read_kernel_setting(
                "/proc/sys/kernel/sysrq",
                "Magic SysRq key",
                "Magic SysRq key is disabled.",
                "Magic SysRq key is ENABLED. It is recommended to disable it.",
            )
        )

        return "\n".join(results)


if __name__ == "__main__":
    SecurityCheck().run()
