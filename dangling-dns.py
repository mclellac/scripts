#!/usr/bin/env python3
"""
DNS Takeover Audit Tool to detect dangling CNAMEs and NS records.
"""
import argparse
import socket
from concurrent.futures import ThreadPoolExecutor

import dns.resolver
import whois
import tldextract
import requests
import urllib3
from rich.console import Console
from rich.table import Table
from rich.style import Style

# Requirements: pip install dnspython python-whois tldextract rich requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console(no_color=False, highlight=False, force_terminal=True)

HTTP_SIGNATURES = {
    "NoSuchBucket": "Amazon S3",
    "The specified bucket does not exist": "Amazon S3",
    "specified key does not exist": "Amazon S3",
    "The sitename you are looking for could not be found": "Azure App Service",
    "404 Web Site not found": "Azure Web App",
    "AccountProfileDoesNotExist": "Azure Storage",
    "The requested URL was not found on this server": "Google Cloud Storage",
    "ghs.googlehosted.com": "Google Apps/Sites",
    "An error occurred while processing your request": "Akamai",
    "Reference #": "Akamai Edge Server",
    "Invalid URL": "Akamai Edge Server",
    "Access Denied": "Akamai WAF",
    "There isn't a GitHub Pages site here": "GitHub Pages",
    "No such app": "Heroku",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SecurityAuditor/1.0"
}

res_obj = dns.resolver.Resolver()

def get_cname_chain(domain):
    """Follows CNAME records to the final destination."""
    chain = []
    current = domain
    while True:
        try:
            answers = res_obj.resolve(current, "CNAME")
            target = str(answers[0].target).strip(".").lower()
            chain.append(target)
            current = target
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            break
    return chain

def get_ip_address(domain):
    """Resolves a domain to its IPv4 address."""
    try:
        answers = res_obj.resolve(domain, "A")
        return str(answers[0])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return "N/A"

def is_buyable(target):
    """Checks if the base domain of a target is available for registration."""
    try:
        ext = tldextract.extract(target)
        base_domain = f"{ext.domain}.{ext.suffix}"
        w = whois.whois(base_domain)
        if not w.registrar and not w.creation_date:
            return True, base_domain
        return False, base_domain
    except Exception:  # pylint: disable=broad-exception-caught
        return True, target

def check_ns_records(domain):
    """Detects if Nameservers are dead or refusing queries."""
    try:
        ns_answers = res_obj.resolve(domain, 'NS')
        for ns in ns_answers:
            ns_target = str(ns.target).strip(".")
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [socket.gethostbyname(ns_target)]
                resolver.resolve('takeover-test.google.com', 'A')
            except (dns.resolver.NoNameservers, dns.resolver.NoAnswer,
                    socket.gaierror):
                return f"VULNERABLE: NS {ns_target} is dead/refusing"
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        pass
    return "Safe"

def extract_server_identity(response):
    """Heuristic to find the server identity across redirect history and headers."""
    for res in [response] + response.history:
        server = res.headers.get("Server") or res.headers.get("server")
        if server and server.lower() != "unknown":
            return server
        if any(k in res.headers for k in ["X-Served-By", "X-Cache-Hits", "X-Timer"]):
            return "Fastly/Varnish"
        if "CF-RAY" in res.headers:
            return "Cloudflare"
        if "X-Akamai-Transformed" in res.headers:
            return "Akamai"
    return "Unknown"

def check_http_dangling(domain, final_target):
    """Checks for service signatures via HTTP/HTTPS and identifies the server."""
    response_text = ""
    server_header = "Unknown"
    status_code = 0
    found_response = False

    for proto in ["https://", "http://"]:
        try:
            r = requests.get(
                f"{proto}{domain}",
                timeout=5,
                verify=False,
                headers=HEADERS,
                allow_redirects=True
            )
            response_text = r.text
            status_code = r.status_code
            server_header = extract_server_identity(r)

            via = r.headers.get("Via", "").lower()
            x_cache = r.headers.get("X-Cache", "").lower()

            if ("cloudfront" in x_cache or "cloudfront" in via) and status_code == 404:
                return True, "VULNERABLE", "Dangling CloudFront", server_header

            found_response = True
            break
        except requests.RequestException:
            continue

    if found_response:
        for sig, provider in HTTP_SIGNATURES.items():
            if sig.lower() in response_text.lower():
                prov_low = provider.lower()
                is_match = (
                    ("google" in prov_low and "google" in final_target) or
                    ("akamai" in prov_low and ("akamai" in final_target or
                                               "edgekey" in final_target)) or
                    ("azure" in prov_low and "azure" in final_target) or
                    ("amazon" in prov_low and "amazonaws" in final_target)
                )
                if is_match:
                    return True, "SUSPECT", f"Dangling {provider}", server_header

    return False, None, None, server_header

def audit_domain(domain):
    """Core logic for detecting dangling infrastructure."""
    results = {
        "domain": domain, "status": "Safe", "details": "Active",
        "reason": "Resolves correctly", "chain": "None", "ip": "N/A",
        "server": "N/A", "color": "green"
    }

    try:
        ns_check = check_ns_records(domain)
        if "VULNERABLE" in ns_check:
            results.update({
                "status": "CRITICAL", "details": "NS Takeover",
                "reason": ns_check, "color": "red"
            })
            return results

        chain = get_cname_chain(domain)
        results["chain"] = " -> ".join(chain) if chain else "Direct A Record"
        final_target = chain[-1] if chain else domain
        results["ip"] = get_ip_address(final_target)

        is_dang, stat, det, srv = check_http_dangling(domain, final_target)
        results["server"] = srv

        if is_dang:
            results.update({
                "status": stat, "details": det, "color": "yellow",
                "reason": f"Active CNAME to abandoned {det} service"
            })
            if stat == "VULNERABLE":
                results["color"] = "bold red"
            return results

        if results["ip"] == "N/A":
            buyable, base_dom = is_buyable(final_target)
            if buyable:
                results.update({
                    "status": "VULNERABLE", "details": f"Buy {base_dom}",
                    "reason": f"Points to unregistered domain {final_target}", "color": "bold red"
                })
            else:
                # Logic to explain WHY it is dangling
                if chain:
                    results.update({
                        "status": "DANGLING", "details": "Broken CNAME",
                        "reason": f"CNAME exists but target '{final_target}' is dead", "color": "orange3"
                    })
                else:
                    results.update({
                        "status": "DANGLING", "details": "Dead A Record",
                        "reason": "Host defined in DNS zone but has no reachable IP address", "color": "orange3"
                    })

    except Exception as e:  # pylint: disable=broad-exception-caught
        results.update({"status": "Error", "details": "Failed",
                        "reason": str(e), "color": "red"})
    return results

def main():
    """CLI Entry point."""
    parser = argparse.ArgumentParser(description="DNS Takeover Audit Tool")
    parser.add_argument("domain", help="The subdomain to audit")
    parser.add_argument("-p", "--publicdns", action="store_true",
                        help="Use 9.9.9.9 for resolution")
    args = parser.parse_args()

    if args.publicdns:
        res_obj.nameservers = ['9.9.9.9']
        console.print("[cyan][b]Using Public DNS: 9.9.9.9[/b][/cyan]")

    header_style = Style(color="white", bold=True, italic=False)
    title_style = Style(bold=True, italic=False)

    table = Table(title="DNS Takeover Audit Results", title_style=title_style)
    table.add_column("Domain", style="cyan", header_style=header_style)
    table.add_column("Status", justify="center", header_style=header_style)
    table.add_column("CNAME Chain", style="blue", header_style=header_style)
    table.add_column("IP Address", style="white", header_style=header_style)
    table.add_column("Server", style="magenta", header_style=header_style)
    table.add_column("Details", header_style=header_style)
    table.add_column("Reason", header_style=header_style)

    with ThreadPoolExecutor(max_workers=5):
        res = audit_domain(args.domain)
        if res:
            status_style = f"{res['color']} bold"
            table.add_row(
                res["domain"], f"[{status_style}]{res['status']}[/]",
                res["chain"], res["ip"], res["server"],
                res["details"], res["reason"]
            )

    console.print(table)

if __name__ == "__main__":
    main()