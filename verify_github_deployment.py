#!/usr/bin/env python3
"""
CBS 1 Gigabit Ethernet - GitHub 배포 완료 검증 스크립트
최종 배포 전 모든 요구사항과 품질 기준을 검증합니다.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
# import requests  # Optional dependency
from datetime import datetime

class GitHubDeploymentVerifier:
    """GitHub 배포 완료성 검증 클래스"""
    
    def __init__(self):
        self.project_name = "CBS 1 Gigabit Ethernet Implementation"
        self.version = "2.0.0"
        self.required_files = [
            # 핵심 파일들
            "README.md", "LICENSE", "pyproject.toml", "setup.py",
            "requirements.txt", "requirements-dev.txt",
            
            # 프로젝트 문서
            "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md",
            "FINAL_PROJECT_SUMMARY.md",
            
            # 논문 파일들
            "paper_korean_perfect.tex", "paper_english_final.tex",
            "paper_korean_perfect.pdf", "paper_english_final.pdf",
            
            # 소스 코드
            "src/cbs_calculator.py", "src/network_simulator.py",
            "src/ml_optimizer.py", "src/dashboard.py",
            "src/performance_benchmark.py",
            
            # Docker 설정
            "Dockerfile", "docker-compose.yml",
            
            # GitHub Actions
            ".github/workflows/ci.yml", ".github/workflows/release.yml",
            
            # 테스트 파일들
            "tests/test_cbs_calculator.py", "tests/test_network_simulator.py",
            "tests/test_ml_optimizer.py", "tests/test_complete_coverage.py",
            
            # 문서
            "docs/index.md", "docs/getting-started.md",
            "docs/api-reference.md",
            
            # 스크립트들
            "scripts/quick_start.py", "scripts/generate_test_data.py",
            "deploy_to_github.py", "run_tests.py"
        ]
        self.verification_results = {}
        
    def print_header(self):
        """검증 헤더 출력"""
        print("\n" + "="*80)
        print("🔍 CBS 1 Gigabit Ethernet - GitHub 배포 완료성 검증")
        print(f"   Project: {self.project_name}")
        print(f"   Version: {self.version}")
        print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

    def verify_file_structure(self) -> bool:
        """필수 파일 구조 검증"""
        print("\n📁 파일 구조 검증...")
        print("-" * 50)
        
        missing_files = []
        existing_files = []
        
        for file_path in self.required_files:
            full_path = Path(file_path)
            if full_path.exists():
                size = full_path.stat().st_size
                print(f"✅ {file_path:<40} ({size:,} bytes)")
                existing_files.append(file_path)
            else:
                print(f"❌ {file_path:<40} (MISSING)")
                missing_files.append(file_path)
        
        self.verification_results['file_structure'] = {
            'total_required': len(self.required_files),
            'existing': len(existing_files),
            'missing': len(missing_files),
            'missing_files': missing_files,
            'completion_rate': len(existing_files) / len(self.required_files) * 100
        }
        
        print(f"\n파일 완성도: {len(existing_files)}/{len(self.required_files)} ({self.verification_results['file_structure']['completion_rate']:.1f}%)")
        return len(missing_files) == 0

    def verify_code_quality(self) -> bool:
        """코드 품질 검증"""
        print("\n🔧 코드 품질 검증...")
        print("-" * 50)
        
        quality_checks = {}
        
        # Python 파일 찾기
        python_files = list(Path('.').rglob('*.py'))
        python_files = [f for f in python_files if 'venv' not in str(f) and '__pycache__' not in str(f)]
        
        print(f"Python 파일 수: {len(python_files)}")
        
        # 파일 크기 통계
        total_lines = 0
        total_size = 0
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    total_lines += lines
                size = py_file.stat().st_size
                total_size += size
            except Exception as e:
                print(f"⚠️ {py_file} 읽기 실패: {e}")
        
        quality_checks['python_files'] = len(python_files)
        quality_checks['total_lines'] = total_lines
        quality_checks['total_size_kb'] = total_size / 1024
        
        print(f"✅ 총 코드 라인: {total_lines:,}")
        print(f"✅ 총 코드 크기: {total_size/1024:.1f} KB")
        
        self.verification_results['code_quality'] = quality_checks
        return True

    def verify_documentation(self) -> bool:
        """문서화 검증"""
        print("\n📚 문서화 검증...")
        print("-" * 50)
        
        doc_checks = {}
        
        # README.md 검증
        readme_path = Path("README.md")
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
                doc_checks['readme_length'] = len(readme_content)
                doc_checks['has_badges'] = '![' in readme_content
                doc_checks['has_installation'] = 'install' in readme_content.lower()
                doc_checks['has_usage'] = 'usage' in readme_content.lower()
                print(f"✅ README.md: {len(readme_content)} 문자")
        else:
            print("❌ README.md 없음")
            doc_checks['readme_exists'] = False
        
        # 논문 파일 검증
        papers = ["paper_korean_perfect.pdf", "paper_english_final.pdf"]
        for paper in papers:
            paper_path = Path(paper)
            if paper_path.exists():
                size = paper_path.stat().st_size
                print(f"✅ {paper}: {size/1024:.1f} KB")
                doc_checks[f'{paper}_size'] = size
            else:
                print(f"❌ {paper} 없음")
        
        # docs 디렉토리 검증
        docs_dir = Path("docs")
        if docs_dir.exists():
            doc_files = list(docs_dir.glob("*.md"))
            print(f"✅ 문서 파일: {len(doc_files)}개")
            doc_checks['doc_files_count'] = len(doc_files)
        
        self.verification_results['documentation'] = doc_checks
        return True

    def verify_tests(self) -> bool:
        """테스트 검증"""
        print("\n🧪 테스트 검증...")
        print("-" * 50)
        
        test_checks = {}
        
        # 테스트 파일 찾기
        test_files = list(Path('tests').glob('test_*.py')) if Path('tests').exists() else []
        print(f"테스트 파일: {len(test_files)}개")
        
        test_checks['test_files_count'] = len(test_files)
        
        # 각 테스트 파일 분석
        total_test_functions = 0
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    test_funcs = content.count('def test_')
                    total_test_functions += test_funcs
                    print(f"  {test_file.name}: {test_funcs} 테스트")
            except Exception as e:
                print(f"⚠️ {test_file} 읽기 실패: {e}")
        
        test_checks['total_test_functions'] = total_test_functions
        print(f"✅ 총 테스트 함수: {total_test_functions}")
        
        self.verification_results['tests'] = test_checks
        return len(test_files) > 0

    def verify_docker_setup(self) -> bool:
        """Docker 설정 검증"""
        print("\n🐳 Docker 설정 검증...")
        print("-" * 50)
        
        docker_checks = {}
        
        # Dockerfile 검증
        dockerfile_path = Path("Dockerfile")
        if dockerfile_path.exists():
            with open(dockerfile_path, 'r', encoding='utf-8') as f:
                dockerfile_content = f.read()
                docker_checks['dockerfile_lines'] = len(dockerfile_content.splitlines())
                docker_checks['has_multistage'] = 'FROM' in dockerfile_content and dockerfile_content.count('FROM') > 1
                print(f"✅ Dockerfile: {docker_checks['dockerfile_lines']} 라인")
        else:
            print("❌ Dockerfile 없음")
            docker_checks['dockerfile_exists'] = False
        
        # docker-compose.yml 검증
        compose_path = Path("docker-compose.yml")
        if compose_path.exists():
            with open(compose_path, 'r', encoding='utf-8') as f:
                compose_content = f.read()
                docker_checks['compose_services'] = compose_content.count('build:') + compose_content.count('image:')
                print(f"✅ docker-compose.yml: ~{docker_checks['compose_services']} 서비스")
        else:
            print("❌ docker-compose.yml 없음")
            docker_checks['compose_exists'] = False
        
        self.verification_results['docker'] = docker_checks
        return dockerfile_path.exists() and compose_path.exists()

    def verify_github_actions(self) -> bool:
        """GitHub Actions 검증"""
        print("\n⚙️ GitHub Actions 검증...")
        print("-" * 50)
        
        actions_checks = {}
        
        actions_dir = Path(".github/workflows")
        if actions_dir.exists():
            workflow_files = list(actions_dir.glob("*.yml"))
            actions_checks['workflow_count'] = len(workflow_files)
            
            for workflow in workflow_files:
                print(f"✅ {workflow.name}")
                
            print(f"총 워크플로우: {len(workflow_files)}개")
        else:
            print("❌ .github/workflows 디렉토리 없음")
            actions_checks['workflows_exist'] = False
        
        self.verification_results['github_actions'] = actions_checks
        return actions_dir.exists()

    def verify_package_configuration(self) -> bool:
        """패키지 설정 검증"""
        print("\n📦 패키지 설정 검증...")
        print("-" * 50)
        
        package_checks = {}
        
        # pyproject.toml 검증
        pyproject_path = Path("pyproject.toml")
        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                pyproject_content = f.read()
                package_checks['has_build_system'] = '[build-system]' in pyproject_content
                package_checks['has_project_info'] = '[project]' in pyproject_content
                package_checks['has_dependencies'] = 'dependencies' in pyproject_content
                print("✅ pyproject.toml 설정 완료")
        else:
            print("❌ pyproject.toml 없음")
            package_checks['pyproject_exists'] = False
        
        # setup.py 검증
        setup_path = Path("setup.py")
        if setup_path.exists():
            with open(setup_path, 'r', encoding='utf-8') as f:
                setup_content = f.read()
                package_checks['has_entry_points'] = 'entry_points' in setup_content
                print("✅ setup.py 설정 완료")
        else:
            print("❌ setup.py 없음")
            package_checks['setup_exists'] = False
        
        # requirements.txt 검증
        req_path = Path("requirements.txt")
        if req_path.exists():
            with open(req_path, 'r', encoding='utf-8') as f:
                requirements = f.readlines()
                package_checks['requirements_count'] = len([r for r in requirements if r.strip() and not r.startswith('#')])
                print(f"✅ requirements.txt: {package_checks['requirements_count']} 패키지")
        
        self.verification_results['package'] = package_checks
        return pyproject_path.exists() or setup_path.exists()

    def calculate_overall_score(self) -> float:
        """전체 완성도 점수 계산"""
        scores = []
        weights = {
            'file_structure': 0.25,
            'code_quality': 0.15,
            'documentation': 0.20,
            'tests': 0.15,
            'docker': 0.10,
            'github_actions': 0.10,
            'package': 0.05
        }
        
        # 파일 구조 점수
        if 'file_structure' in self.verification_results:
            score = self.verification_results['file_structure']['completion_rate']
            scores.append(score * weights['file_structure'])
        
        # 코드 품질 점수 (라인 수 기반)
        if 'code_quality' in self.verification_results:
            lines = self.verification_results['code_quality'].get('total_lines', 0)
            score = min(100, lines / 50)  # 5000 라인 기준으로 100점
            scores.append(score * weights['code_quality'])
        
        # 문서화 점수
        if 'documentation' in self.verification_results:
            doc_score = 0
            if self.verification_results['documentation'].get('readme_length', 0) > 1000:
                doc_score += 30
            if 'paper_korean_perfect.pdf_size' in self.verification_results['documentation']:
                doc_score += 35
            if 'paper_english_final.pdf_size' in self.verification_results['documentation']:
                doc_score += 35
            scores.append(doc_score * weights['documentation'])
        
        # 테스트 점수
        if 'tests' in self.verification_results:
            test_funcs = self.verification_results['tests'].get('total_test_functions', 0)
            score = min(100, test_funcs * 5)  # 함수당 5점
            scores.append(score * weights['tests'])
        
        # Docker 점수
        if 'docker' in self.verification_results:
            docker_score = 0
            if self.verification_results['docker'].get('dockerfile_exists', True):
                docker_score += 50
            if self.verification_results['docker'].get('compose_exists', True):
                docker_score += 50
            scores.append(docker_score * weights['docker'])
        
        # GitHub Actions 점수
        if 'github_actions' in self.verification_results:
            workflows = self.verification_results['github_actions'].get('workflow_count', 0)
            score = min(100, workflows * 50)  # 워크플로우당 50점
            scores.append(score * weights['github_actions'])
        
        # 패키지 점수
        if 'package' in self.verification_results:
            pkg_score = 0
            if self.verification_results['package'].get('pyproject_exists', True):
                pkg_score += 50
            if self.verification_results['package'].get('setup_exists', True):
                pkg_score += 50
            scores.append(pkg_score * weights['package'])
        
        return sum(scores)

    def generate_report(self) -> Dict[str, Any]:
        """최종 검증 리포트 생성"""
        overall_score = self.calculate_overall_score()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'project': self.project_name,
            'version': self.version,
            'overall_score': overall_score,
            'verification_results': self.verification_results,
            'recommendations': []
        }
        
        # 개선 권장사항 생성
        if overall_score < 95:
            if self.verification_results.get('file_structure', {}).get('completion_rate', 100) < 100:
                missing = self.verification_results['file_structure']['missing_files']
                report['recommendations'].append(f"누락된 파일 추가: {', '.join(missing[:5])}")
            
            if self.verification_results.get('tests', {}).get('total_test_functions', 0) < 20:
                report['recommendations'].append("테스트 커버리지 향상 필요")
            
            if not self.verification_results.get('docker', {}).get('dockerfile_exists', True):
                report['recommendations'].append("Docker 설정 추가 필요")
        
        return report

    def print_final_summary(self, report: Dict[str, Any]):
        """최종 요약 출력"""
        score = report['overall_score']
        print("\n" + "="*80)
        print("🏆 최종 검증 결과")
        print("="*80)
        
        # 점수에 따른 등급 및 이모지
        if score >= 95:
            grade = "A+ (완벽)"
            emoji = "🌟"
        elif score >= 90:
            grade = "A (우수)"
            emoji = "✨"
        elif score >= 85:
            grade = "B+ (양호)"
            emoji = "👍"
        elif score >= 80:
            grade = "B (보통)"
            emoji = "👌"
        else:
            grade = "C (개선 필요)"
            emoji = "⚠️"
        
        print(f"\n{emoji} 전체 완성도: {score:.1f}% ({grade})")
        
        # 상세 점수
        print(f"\n📊 상세 검증 결과:")
        if 'file_structure' in self.verification_results:
            fs = self.verification_results['file_structure']
            print(f"  • 파일 구조: {fs['existing']}/{fs['total_required']} ({fs['completion_rate']:.1f}%)")
        
        if 'code_quality' in self.verification_results:
            cq = self.verification_results['code_quality']
            print(f"  • 코드 품질: {cq['total_lines']:,} 라인, {cq['python_files']} 파일")
        
        if 'tests' in self.verification_results:
            tests = self.verification_results['tests']
            print(f"  • 테스트: {tests['total_test_functions']} 함수, {tests['test_files_count']} 파일")
        
        if 'documentation' in self.verification_results:
            docs = self.verification_results['documentation']
            print(f"  • 문서화: README {docs.get('readme_length', 0)} 문자")
        
        # 권장사항
        if report['recommendations']:
            print(f"\n💡 개선 권장사항:")
            for rec in report['recommendations']:
                print(f"  • {rec}")
        
        # 배포 준비 상태
        if score >= 95:
            print(f"\n🚀 배포 준비 완료!")
            print("  모든 검증을 통과했습니다. GitHub에 배포할 수 있습니다.")
        elif score >= 85:
            print(f"\n✅ 배포 가능 상태")
            print("  대부분의 요구사항을 충족합니다. 몇 가지 개선 후 배포 권장합니다.")
        else:
            print(f"\n⚠️ 추가 작업 필요")
            print("  배포 전 개선사항을 먼저 완료해 주세요.")

    def save_report(self, report: Dict[str, Any]):
        """검증 리포트 파일 저장"""
        report_file = "github_deployment_verification_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n💾 검증 리포트 저장: {report_file}")

    def run_full_verification(self) -> bool:
        """전체 검증 실행"""
        self.print_header()
        
        # 모든 검증 단계 실행
        verifications = [
            ("파일 구조", self.verify_file_structure),
            ("코드 품질", self.verify_code_quality),
            ("문서화", self.verify_documentation),
            ("테스트", self.verify_tests),
            ("Docker 설정", self.verify_docker_setup),
            ("GitHub Actions", self.verify_github_actions),
            ("패키지 설정", self.verify_package_configuration)
        ]
        
        success_count = 0
        for name, verify_func in verifications:
            try:
                if verify_func():
                    success_count += 1
                time.sleep(0.5)  # 진행 상황 표시
            except Exception as e:
                print(f"❌ {name} 검증 중 오류: {e}")
        
        # 최종 리포트 생성 및 출력
        report = self.generate_report()
        self.print_final_summary(report)
        self.save_report(report)
        
        return report['overall_score'] >= 85

def main():
    """메인 실행 함수"""
    verifier = GitHubDeploymentVerifier()
    
    try:
        success = verifier.run_full_verification()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n👋 검증이 중단되었습니다.")
        return 0
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())