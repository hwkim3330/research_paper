#!/usr/bin/env python3
"""
CBS 1 Gigabit Ethernet - 자동화된 릴리즈 준비 상태 검사기
GitHub 릴리즈 전 모든 체크리스트 항목을 자동으로 검증합니다.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
# import requests  # Optional dependency
from datetime import datetime
import tempfile
import shutil

class ReleaseReadinessChecker:
    """릴리즈 준비 상태 자동 검사 클래스"""
    
    def __init__(self):
        self.project_name = "CBS 1 Gigabit Ethernet Implementation"
        self.version = "2.0.0"
        self.target_repo = "hwkim3330/research_paper"
        self.check_results = {}
        self.failed_checks = []
        self.warnings = []
        
    def print_header(self):
        """헤더 출력"""
        print("\n" + "="*80)
        print("🚀 CBS 1 Gigabit Ethernet - 릴리즈 준비 상태 검사")
        print(f"   Project: {self.project_name}")
        print(f"   Version: {self.version}")
        print(f"   Target: github.com/{self.target_repo}")
        print(f"   Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

    def check_critical_files(self) -> bool:
        """필수 파일들 존재 확인"""
        print("\n📋 필수 파일 검사...")
        print("-" * 50)
        
        critical_files = [
            # 프로젝트 핵심
            ('README.md', '프로젝트 메인 문서'),
            ('LICENSE', '라이센스 파일'),
            ('pyproject.toml', 'Python 패키지 설정'),
            ('requirements.txt', '의존성 목록'),
            
            # 논문
            ('paper_korean_perfect.tex', '한국어 논문 LaTeX'),
            ('paper_english_final.tex', '영어 논문 LaTeX'),
            ('paper_korean_perfect.pdf', '한국어 논문 PDF'),
            ('paper_english_final.pdf', '영어 논문 PDF'),
            
            # 핵심 구현
            ('src/cbs_calculator.py', 'CBS 계산기'),
            ('src/network_simulator.py', '네트워크 시뮬레이터'),
            ('src/ml_optimizer.py', 'ML 최적화기'),
            
            # Docker
            ('Dockerfile', 'Docker 설정'),
            ('docker-compose.yml', 'Docker Compose 설정'),
            
            # GitHub
            ('.github/workflows/ci.yml', 'CI 워크플로우'),
            ('CONTRIBUTING.md', '기여 가이드'),
            ('SECURITY.md', '보안 정책')
        ]
        
        missing_files = []
        existing_files = []
        
        for file_path, description in critical_files:
            if Path(file_path).exists():
                print(f"✅ {description:<25} ({file_path})")
                existing_files.append((file_path, description))
            else:
                print(f"❌ {description:<25} ({file_path}) - MISSING")
                missing_files.append((file_path, description))
                self.failed_checks.append(f"Missing critical file: {file_path}")
        
        self.check_results['critical_files'] = {
            'total': len(critical_files),
            'existing': len(existing_files),
            'missing': len(missing_files),
            'missing_list': missing_files
        }
        
        success = len(missing_files) == 0
        print(f"\n필수 파일 완성도: {len(existing_files)}/{len(critical_files)}")
        return success

    def check_code_quality(self) -> bool:
        """코드 품질 검사"""
        print("\n🔧 코드 품질 검사...")
        print("-" * 50)
        
        quality_passed = True
        
        # Python 파일 찾기
        python_files = list(Path('src').glob('*.py')) if Path('src').exists() else []
        
        if len(python_files) == 0:
            print("❌ src/ 디렉토리에 Python 파일이 없습니다")
            self.failed_checks.append("No Python files in src/")
            return False
        
        print(f"Python 파일 수: {len(python_files)}")
        
        # 각 파일의 기본 품질 검사
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 기본 품질 검사
                has_docstring = '"""' in content or "'''" in content
                has_imports = 'import ' in content
                has_functions = 'def ' in content
                has_classes = 'class ' in content
                
                if not has_docstring:
                    self.warnings.append(f"{py_file.name}: No docstrings found")
                
                if not (has_functions or has_classes):
                    self.warnings.append(f"{py_file.name}: No functions or classes found")
                
                print(f"  {py_file.name}: {len(content.splitlines())} 라인")
                
            except Exception as e:
                print(f"❌ {py_file} 읽기 실패: {e}")
                quality_passed = False
        
        self.check_results['code_quality'] = {
            'python_files': len(python_files),
            'quality_passed': quality_passed
        }
        
        return quality_passed

    def check_documentation_quality(self) -> bool:
        """문서 품질 검사"""
        print("\n📚 문서 품질 검사...")
        print("-" * 50)
        
        doc_quality = True
        
        # README.md 상세 검사
        readme_path = Path('README.md')
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
            
            required_sections = [
                ('# ', '제목'),
                ('## ', '섹션 헤더'),
                ('install', '설치 가이드'),
                ('usage', '사용법'),
                ('example', '예제')
            ]
            
            readme_score = 0
            for pattern, description in required_sections:
                if pattern.lower() in readme_content.lower():
                    print(f"✅ README: {description} 포함")
                    readme_score += 1
                else:
                    print(f"⚠️ README: {description} 누락")
                    self.warnings.append(f"README missing: {description}")
            
            print(f"README 품질: {readme_score}/{len(required_sections)}")
            
            # README 길이 검사
            if len(readme_content) < 1000:
                self.warnings.append("README too short (< 1000 characters)")
            
        else:
            print("❌ README.md 파일이 없습니다")
            self.failed_checks.append("Missing README.md")
            doc_quality = False
        
        # 논문 PDF 검사
        papers = ['paper_korean_perfect.pdf', 'paper_english_final.pdf']
        for paper in papers:
            paper_path = Path(paper)
            if paper_path.exists():
                size_mb = paper_path.stat().st_size / 1024 / 1024
                print(f"✅ {paper}: {size_mb:.1f} MB")
                if size_mb < 0.5:
                    self.warnings.append(f"{paper} seems too small ({size_mb:.1f} MB)")
            else:
                print(f"❌ {paper}: 누락")
                self.failed_checks.append(f"Missing paper: {paper}")
                doc_quality = False
        
        self.check_results['documentation'] = {
            'readme_exists': readme_path.exists(),
            'papers_count': len([p for p in papers if Path(p).exists()]),
            'quality_passed': doc_quality
        }
        
        return doc_quality

    def check_test_completeness(self) -> bool:
        """테스트 완성도 검사"""
        print("\n🧪 테스트 완성도 검사...")
        print("-" * 50)
        
        test_quality = True
        
        # 테스트 디렉토리 확인
        test_dir = Path('tests')
        if not test_dir.exists():
            print("❌ tests/ 디렉토리가 없습니다")
            self.failed_checks.append("Missing tests/ directory")
            return False
        
        # 테스트 파일들 확인
        test_files = list(test_dir.glob('test_*.py'))
        print(f"테스트 파일: {len(test_files)}개")
        
        if len(test_files) == 0:
            print("❌ 테스트 파일이 없습니다")
            self.failed_checks.append("No test files found")
            return False
        
        # 각 핵심 모듈에 대응하는 테스트 확인
        core_modules = ['cbs_calculator', 'network_simulator', 'ml_optimizer']
        missing_tests = []
        
        for module in core_modules:
            test_file = test_dir / f'test_{module}.py'
            if test_file.exists():
                print(f"✅ {module} 테스트 존재")
            else:
                print(f"⚠️ {module} 테스트 누락")
                missing_tests.append(module)
                self.warnings.append(f"Missing test for {module}")
        
        # 테스트 함수 수 계산
        total_test_functions = 0
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    test_count = content.count('def test_')
                    total_test_functions += test_count
                    print(f"  {test_file.name}: {test_count} 테스트")
            except Exception as e:
                print(f"❌ {test_file} 읽기 실패: {e}")
                test_quality = False
        
        print(f"총 테스트 함수: {total_test_functions}")
        
        if total_test_functions < 10:
            self.warnings.append(f"Low test count: {total_test_functions} (recommended: 10+)")
        
        self.check_results['tests'] = {
            'test_files': len(test_files),
            'test_functions': total_test_functions,
            'missing_tests': missing_tests,
            'quality_passed': test_quality
        }
        
        return test_quality

    def check_docker_configuration(self) -> bool:
        """Docker 설정 검사"""
        print("\n🐳 Docker 설정 검사...")
        print("-" * 50)
        
        docker_quality = True
        
        # Dockerfile 검사
        dockerfile_path = Path('Dockerfile')
        if dockerfile_path.exists():
            with open(dockerfile_path, 'r', encoding='utf-8') as f:
                dockerfile_content = f.read()
            
            required_elements = [
                ('FROM', '베이스 이미지'),
                ('COPY', '파일 복사'),
                ('RUN', '명령 실행'),
                ('EXPOSE', '포트 노출'),
                ('CMD', '실행 명령')
            ]
            
            for element, description in required_elements:
                if element in dockerfile_content:
                    print(f"✅ Dockerfile: {description} 포함")
                else:
                    print(f"⚠️ Dockerfile: {description} 누락")
                    self.warnings.append(f"Dockerfile missing: {description}")
        else:
            print("❌ Dockerfile이 없습니다")
            self.failed_checks.append("Missing Dockerfile")
            docker_quality = False
        
        # docker-compose.yml 검사
        compose_path = Path('docker-compose.yml')
        if compose_path.exists():
            with open(compose_path, 'r', encoding='utf-8') as f:
                compose_content = f.read()
            
            services_count = compose_content.count('build:') + compose_content.count('image:')
            print(f"✅ docker-compose.yml: ~{services_count} 서비스")
            
            if services_count < 2:
                self.warnings.append("docker-compose has few services")
        else:
            print("❌ docker-compose.yml이 없습니다")
            self.failed_checks.append("Missing docker-compose.yml")
            docker_quality = False
        
        self.check_results['docker'] = {
            'dockerfile_exists': dockerfile_path.exists(),
            'compose_exists': compose_path.exists(),
            'quality_passed': docker_quality
        }
        
        return docker_quality

    def check_github_integration(self) -> bool:
        """GitHub 통합 검사"""
        print("\n⚙️ GitHub 통합 검사...")
        print("-" * 50)
        
        github_quality = True
        
        # GitHub Actions 워크플로우 검사
        workflows_dir = Path('.github/workflows')
        if workflows_dir.exists():
            workflow_files = list(workflows_dir.glob('*.yml'))
            print(f"GitHub Actions 워크플로우: {len(workflow_files)}개")
            
            for workflow in workflow_files:
                print(f"  ✅ {workflow.name}")
                
            if len(workflow_files) == 0:
                self.warnings.append("No GitHub Actions workflows found")
        else:
            print("⚠️ .github/workflows 디렉토리가 없습니다")
            self.warnings.append("Missing GitHub Actions workflows")
        
        # 기타 GitHub 파일들
        github_files = [
            ('CONTRIBUTING.md', '기여 가이드'),
            ('SECURITY.md', '보안 정책'),
            ('.github/ISSUE_TEMPLATE', '이슈 템플릿'),
            ('.github/PULL_REQUEST_TEMPLATE.md', 'PR 템플릿')
        ]
        
        for file_path, description in github_files:
            if Path(file_path).exists():
                print(f"✅ {description}")
            else:
                print(f"⚠️ {description} 누락")
                self.warnings.append(f"Missing {description}")
        
        self.check_results['github'] = {
            'workflows_count': len(workflow_files) if workflows_dir.exists() else 0,
            'has_contributing': Path('CONTRIBUTING.md').exists(),
            'has_security': Path('SECURITY.md').exists(),
            'quality_passed': github_quality
        }
        
        return github_quality

    def check_version_consistency(self) -> bool:
        """버전 일관성 검사"""
        print("\n🔢 버전 일관성 검사...")
        print("-" * 50)
        
        version_files = {}
        version_consistent = True
        
        # pyproject.toml 버전
        pyproject_path = Path('pyproject.toml')
        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # version = "2.0.0" 패턴 찾기
                import re
                version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if version_match:
                    version_files['pyproject.toml'] = version_match.group(1)
        
        # setup.py 버전 (있는 경우)
        setup_path = Path('setup.py')
        if setup_path.exists():
            with open(setup_path, 'r', encoding='utf-8') as f:
                content = f.read()
                version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if version_match:
                    version_files['setup.py'] = version_match.group(1)
        
        # 버전 일관성 확인
        if len(version_files) > 1:
            versions = list(version_files.values())
            if len(set(versions)) == 1:
                print(f"✅ 모든 파일에서 버전 일치: {versions[0]}")
            else:
                print("❌ 버전 불일치 발견:")
                for file, version in version_files.items():
                    print(f"  {file}: {version}")
                self.failed_checks.append("Version inconsistency")
                version_consistent = False
        else:
            print("⚠️ 버전 정보를 찾을 수 없습니다")
            self.warnings.append("No version information found")
        
        self.check_results['version'] = {
            'version_files': version_files,
            'consistent': version_consistent,
            'target_version': self.version
        }
        
        return version_consistent

    def check_security_practices(self) -> bool:
        """보안 관행 검사"""
        print("\n🔒 보안 관행 검사...")
        print("-" * 50)
        
        security_ok = True
        
        # 민감한 정보 검사 패턴들
        sensitive_patterns = [
            (r'password\s*=\s*["\'][^"\']*["\']', '하드코딩된 패스워드'),
            (r'api_key\s*=\s*["\'][^"\']*["\']', 'API 키'),
            (r'secret\s*=\s*["\'][^"\']*["\']', '시크릿 키'),
            (r'token\s*=\s*["\'][^"\']*["\']', '토큰'),
            (r'["\'][A-Za-z0-9+/]{20,}={0,2}["\']', 'Base64 인코딩된 시크릿')
        ]
        
        # Python 파일들에서 민감한 정보 검사
        python_files = list(Path('.').rglob('*.py'))
        python_files = [f for f in python_files if 'venv' not in str(f) and '__pycache__' not in str(f)]
        
        security_issues = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for pattern, description in sensitive_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        security_issues.append(f"{py_file}: {description}")
                        
            except Exception as e:
                continue
        
        if security_issues:
            print("❌ 보안 이슈 발견:")
            for issue in security_issues:
                print(f"  {issue}")
            self.failed_checks.extend(security_issues)
            security_ok = False
        else:
            print("✅ 하드코딩된 시크릿 없음")
        
        # SECURITY.md 존재 확인
        if Path('SECURITY.md').exists():
            print("✅ 보안 정책 문서 존재")
        else:
            print("⚠️ SECURITY.md 파일 누락")
            self.warnings.append("Missing SECURITY.md")
        
        self.check_results['security'] = {
            'issues_found': len(security_issues),
            'has_security_md': Path('SECURITY.md').exists(),
            'security_passed': security_ok
        }
        
        return security_ok

    def calculate_readiness_score(self) -> float:
        """릴리즈 준비 점수 계산"""
        total_score = 0
        max_score = 0
        
        # 각 검사 항목별 가중치
        weights = {
            'critical_files': 30,
            'code_quality': 15,
            'documentation': 20,
            'tests': 15,
            'docker': 10,
            'github': 5,
            'version': 3,
            'security': 2
        }
        
        for check_name, weight in weights.items():
            max_score += weight
            
            if check_name in self.check_results:
                result = self.check_results[check_name]
                
                if check_name == 'critical_files':
                    completion = result['existing'] / result['total']
                    total_score += weight * completion
                    
                elif check_name == 'documentation':
                    if result['quality_passed'] and result['papers_count'] >= 2:
                        total_score += weight
                    elif result['quality_passed']:
                        total_score += weight * 0.7
                        
                elif check_name == 'tests':
                    if result['quality_passed'] and result['test_functions'] >= 10:
                        total_score += weight
                    elif result['quality_passed']:
                        total_score += weight * 0.8
                        
                else:
                    if result.get('quality_passed', False) or result.get('consistent', False) or result.get('security_passed', False):
                        total_score += weight
        
        return (total_score / max_score) * 100 if max_score > 0 else 0

    def generate_readiness_report(self) -> Dict[str, Any]:
        """릴리즈 준비 리포트 생성"""
        readiness_score = self.calculate_readiness_score()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'project': self.project_name,
            'version': self.version,
            'readiness_score': readiness_score,
            'check_results': self.check_results,
            'failed_checks': self.failed_checks,
            'warnings': self.warnings,
            'recommendation': self.get_release_recommendation(readiness_score)
        }
        
        return report

    def get_release_recommendation(self, score: float) -> str:
        """릴리즈 권장사항 생성"""
        if score >= 95:
            return "READY - 릴리즈 준비 완료. 즉시 배포 가능합니다."
        elif score >= 85:
            return "MOSTLY_READY - 대부분 준비됨. 경고사항 검토 후 배포 권장."
        elif score >= 70:
            return "NEEDS_WORK - 주요 이슈 해결 필요. 릴리즈 전 개선 권장."
        else:
            return "NOT_READY - 중요한 문제들이 있음. 릴리즈 전 반드시 수정 필요."

    def print_final_assessment(self, report: Dict[str, Any]):
        """최종 평가 출력"""
        score = report['readiness_score']
        recommendation = report['recommendation']
        
        print("\n" + "="*80)
        print("🏆 최종 릴리즈 준비 평가")
        print("="*80)
        
        # 점수에 따른 색상/이모지
        if score >= 95:
            status_emoji = "🌟"
        elif score >= 85:
            status_emoji = "✅"
        elif score >= 70:
            status_emoji = "⚠️"
        else:
            status_emoji = "❌"
        
        print(f"\n{status_emoji} 릴리즈 준비 점수: {score:.1f}/100")
        print(f"📋 권장사항: {recommendation}")
        
        # 실패한 검사들
        if self.failed_checks:
            print(f"\n❌ 해결 필요한 이슈 ({len(self.failed_checks)}개):")
            for i, issue in enumerate(self.failed_checks[:10], 1):  # 최대 10개만 표시
                print(f"  {i}. {issue}")
            if len(self.failed_checks) > 10:
                print(f"  ... 외 {len(self.failed_checks) - 10}개 추가")
        
        # 경고사항들
        if self.warnings:
            print(f"\n⚠️ 권장 개선사항 ({len(self.warnings)}개):")
            for i, warning in enumerate(self.warnings[:5], 1):  # 최대 5개만 표시
                print(f"  {i}. {warning}")
            if len(self.warnings) > 5:
                print(f"  ... 외 {len(self.warnings) - 5}개 추가")
        
        # 다음 단계 안내
        print(f"\n🚀 다음 단계:")
        if score >= 95:
            print("  1. GitHub에 코드 푸시")
            print("  2. 릴리즈 태그 생성")
            print("  3. GitHub Release 생성")
            print("  4. PyPI 배포 (선택)")
        elif score >= 85:
            print("  1. 경고사항 검토 및 개선")
            print("  2. 릴리즈 준비 재검사")
            print("  3. GitHub 배포 진행")
        else:
            print("  1. 실패한 검사 항목 수정")
            print("  2. 릴리즈 준비 재검사")
            print("  3. 점수 95+ 달성 후 배포")

    def save_report(self, report: Dict[str, Any]):
        """리포트 파일 저장"""
        report_file = "release_readiness_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 상세 리포트 저장: {report_file}")

    def run_full_check(self) -> bool:
        """전체 검사 실행"""
        self.print_header()
        
        # 모든 검사 실행
        checks = [
            ("필수 파일", self.check_critical_files),
            ("코드 품질", self.check_code_quality),
            ("문서 품질", self.check_documentation_quality),
            ("테스트 완성도", self.check_test_completeness),
            ("Docker 설정", self.check_docker_configuration),
            ("GitHub 통합", self.check_github_integration),
            ("버전 일관성", self.check_version_consistency),
            ("보안 관행", self.check_security_practices)
        ]
        
        for name, check_func in checks:
            try:
                check_func()
                time.sleep(0.3)  # 진행 표시
            except Exception as e:
                print(f"❌ {name} 검사 중 오류: {e}")
                self.failed_checks.append(f"{name} check failed: {str(e)}")
        
        # 최종 리포트 생성 및 출력
        report = self.generate_readiness_report()
        self.print_final_assessment(report)
        self.save_report(report)
        
        return report['readiness_score'] >= 85

def main():
    """메인 실행 함수"""
    checker = ReleaseReadinessChecker()
    
    try:
        ready = checker.run_full_check()
        return 0 if ready else 1
        
    except KeyboardInterrupt:
        print("\n\n👋 검사가 중단되었습니다.")
        return 0
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())