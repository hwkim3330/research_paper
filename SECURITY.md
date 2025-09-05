# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | ✅ Yes             |
| 1.5.x   | ❌ No (EOL)        |
| < 1.5   | ❌ No              |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in the CBS 1 Gigabit Ethernet implementation, please report it responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. Email us at: `security@cbs-research.example.com`
3. Include detailed information about the vulnerability
4. Provide steps to reproduce if possible

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)
- Your contact information

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Status Updates**: Every 2 weeks
- **Fix Timeline**: Depends on severity

### Security Considerations

#### Network Security
- All network communications should be encrypted
- Default credentials must be changed
- Access controls should be properly configured

#### Code Security
- Input validation is performed on all user inputs
- Buffer overflow protections are implemented
- No hardcoded credentials in source code

#### Hardware Security
- Secure boot processes recommended
- Hardware security modules (HSM) support
- Physical access controls for network equipment

## Security Updates

Security updates will be released as patch versions and announced through:
- GitHub Security Advisories
- Release notes
- Security mailing list

## Responsible Disclosure

We follow responsible disclosure principles:
1. Report received and acknowledged
2. Vulnerability assessed and reproduced
3. Fix developed and tested
4. Coordinated disclosure timeline agreed
5. Public disclosure with credit to reporter