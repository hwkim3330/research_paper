# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this CBS TSN research project, please report it responsibly:

1. **Do NOT** open a public issue
2. Send an email to: security@research-project.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge your report within 48 hours and provide updates on our progress.

## Security Considerations

This project implements network protocols and hardware interfaces. Please be aware:

- CBS configurations can affect network performance
- Incorrect parameters may impact other traffic
- Hardware access requires proper authorization
- NETCONF/YANG interfaces should be secured

## Safe Usage

- Always test configurations in isolated environments
- Validate CBS parameters before deployment
- Monitor network performance after changes
- Use secure communication channels for management