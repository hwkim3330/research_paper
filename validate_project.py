#!/usr/bin/env python3
"""
프로젝트 검증 및 완성도 확인 스크립트
모든 파일과 기능이 제대로 구현되었는지 확인
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess

class ProjectValidator:
    """프로젝트 검증 도구"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.validation_results = {}
        
    def check_file_exists(self, filepath: str) -> bool:
        """파일 존재 확인"""
        return (self.project_root / filepath).exists()
    
    def check_python_syntax(self, filepath: str) -> Tuple[bool, str]:
        """Python 파일 문법 검사"""
        try:
            with open(self.project_root / filepath, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, filepath, 'exec')
            return True, "OK"
        except SyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def validate_core_files(self) -> Dict:
        """핵심 파일 검증"""
        print("\n📁 핵심 파일 검증")
        print("=" * 50)
        
        core_files = {
            "CBS 계산기": "src/cbs_calculator.py",
            "네트워크 시뮬레이터": "src/network_simulator.py",
            "ML 최적화기": "src/ml_optimizer.py",
            "대시보드": "src/dashboard.py",
            "성능 벤치마크": "src/performance_benchmark.py",
            "하드웨어 테스트": "hardware/lan9662_cbs_test.py"
        }
        
        results = {}
        for name, filepath in core_files.items():
            exists = self.check_file_exists(filepath)
            if exists:
                valid, error = self.check_python_syntax(filepath)
                if valid:
                    status = "✅ 정상"
                    details = "파일 존재, 문법 정상"
                else:
                    status = "⚠️ 문법 오류"
                    details = error
            else:
                status = "❌ 파일 없음"
                details = "파일이 존재하지 않음"
            
            results[name] = {
                "status": status,
                "filepath": filepath,
                "details": details
            }
            
            print(f"  {name}: {status}")
            if status != "✅ 정상":
                print(f"    └─ {details}")
        
        return results
    
    def validate_papers(self) -> Dict:
        """논문 파일 검증"""
        print("\n📄 논문 파일 검증")
        print("=" * 50)
        
        paper_files = {
            "한국어 논문 (완벽판)": "paper_korean_perfect.tex",
            "영어 논문 (최종)": "paper_english_final.tex",
            "한국어 논문 (개선)": "paper_korean_improved.tex",
            "한국어 논문 (최종)": "paper_korean_final.tex"
        }
        
        results = {}
        for name, filepath in paper_files.items():
            exists = self.check_file_exists(filepath)
            if exists:
                file_path = self.project_root / filepath
                size = file_path.stat().st_size
                lines = len(file_path.read_text(encoding='utf-8', errors='ignore').splitlines())
                status = "✅ 정상"
                details = f"{size:,} bytes, {lines:,} lines"
            else:
                status = "❌ 파일 없음"
                details = "파일이 존재하지 않음"
            
            results[name] = {
                "status": status,
                "filepath": filepath,
                "details": details
            }
            
            print(f"  {name}: {status}")
            if status == "✅ 정상":
                print(f"    └─ {details}")
        
        return results
    
    def validate_docker(self) -> Dict:
        """Docker 설정 검증"""
        print("\n🐳 Docker 설정 검증")
        print("=" * 50)
        
        docker_files = {
            "Dockerfile": "Dockerfile",
            "Docker Compose": "docker-compose.yml"
        }
        
        results = {}
        for name, filepath in docker_files.items():
            exists = self.check_file_exists(filepath)
            if exists:
                file_path = self.project_root / filepath
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                if filepath == "docker-compose.yml":
                    try:
                        yaml.safe_load(content)
                        status = "✅ 정상"
                        details = "YAML 형식 정상"
                    except yaml.YAMLError as e:
                        status = "⚠️ YAML 오류"
                        details = str(e)
                else:
                    status = "✅ 정상"
                    details = f"{len(content.splitlines())} lines"
            else:
                status = "❌ 파일 없음"
                details = "파일이 존재하지 않음"
            
            results[name] = {
                "status": status,
                "filepath": filepath,
                "details": details
            }
            
            print(f"  {name}: {status}")
            if status != "✅ 정상":
                print(f"    └─ {details}")
        
        return results
    
    def validate_tests(self) -> Dict:
        """테스트 파일 검증"""
        print("\n🧪 테스트 파일 검증")
        print("=" * 50)
        
        test_files = {
            "통합 테스트": "tests/test_complete_coverage.py",
            "CBS 테스트": "tests/test_cbs_calculator.py",
            "시뮬레이터 테스트": "tests/test_network_simulator.py"
        }
        
        results = {}
        for name, filepath in test_files.items():
            exists = self.check_file_exists(filepath)
            if exists:
                valid, error = self.check_python_syntax(filepath)
                if valid:
                    status = "✅ 정상"
                    details = "테스트 파일 문법 정상"
                else:
                    status = "⚠️ 문법 오류"
                    details = error
            else:
                status = "❌ 파일 없음"
                details = "파일이 존재하지 않음"
            
            results[name] = {
                "status": status,
                "filepath": filepath,
                "details": details
            }
            
            print(f"  {name}: {status}")
        
        return results
    
    def validate_documentation(self) -> Dict:
        """문서 검증"""
        print("\n📚 문서 검증")
        print("=" * 50)
        
        doc_files = {
            "README": "README.md",
            "특허 문서": "patents/cbs_patent_application.md",
            "프로젝트 상태": "ULTIMATE_PROJECT_STATUS.md"
        }
        
        results = {}
        for name, filepath in doc_files.items():
            exists = self.check_file_exists(filepath)
            if exists:
                file_path = self.project_root / filepath
                size = file_path.stat().st_size
                status = "✅ 정상"
                details = f"{size:,} bytes"
            else:
                status = "❌ 파일 없음"
                details = "파일이 존재하지 않음"
            
            results[name] = {
                "status": status,
                "filepath": filepath,
                "details": details
            }
            
            print(f"  {name}: {status}")
        
        return results
    
    def calculate_completeness(self) -> Dict:
        """프로젝트 완성도 계산"""
        print("\n📊 프로젝트 완성도 분석")
        print("=" * 50)
        
        all_results = {
            "핵심 파일": self.validate_core_files(),
            "논문": self.validate_papers(),
            "Docker": self.validate_docker(),
            "테스트": self.validate_tests(),
            "문서": self.validate_documentation()
        }
        
        # 통계 계산
        total_items = 0
        completed_items = 0
        warning_items = 0
        missing_items = 0
        
        for category, items in all_results.items():
            for item_name, item_data in items.items():
                total_items += 1
                if "✅" in item_data["status"]:
                    completed_items += 1
                elif "⚠️" in item_data["status"]:
                    warning_items += 1
                else:
                    missing_items += 1
        
        completeness = (completed_items / total_items) * 100 if total_items > 0 else 0
        
        print(f"\n📈 완성도 통계:")
        print(f"  전체 항목: {total_items}")
        print(f"  완료: {completed_items} ✅")
        print(f"  경고: {warning_items} ⚠️")
        print(f"  누락: {missing_items} ❌")
        print(f"\n  🎯 완성도: {completeness:.1f}%")
        
        if completeness >= 90:
            print("\n  🏆 프로젝트 완성도 우수!")
        elif completeness >= 70:
            print("\n  📝 추가 작업 필요")
        else:
            print("\n  ⚠️ 상당한 작업 필요")
        
        return {
            "total": total_items,
            "completed": completed_items,
            "warnings": warning_items,
            "missing": missing_items,
            "completeness": completeness,
            "details": all_results
        }
    
    def generate_report(self) -> None:
        """최종 보고서 생성"""
        print("\n" + "="*60)
        print(" 프로젝트 검증 보고서 ")
        print("="*60)
        
        results = self.calculate_completeness()
        
        # JSON 보고서 저장
        report_file = "project_validation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 보고서 저장: {report_file}")
        
        # 권장 사항
        print("\n💡 권장 사항:")
        if results["missing"] > 0:
            print("  1. 누락된 파일 생성 또는 복구")
        if results["warnings"] > 0:
            print("  2. 경고 항목 수정")
        print("  3. 모든 테스트 실행 및 통과 확인")
        print("  4. 문서 최신화")
        
        print("\n" + "="*60)
        print(" 검증 완료 ")
        print("="*60)

def main():
    """메인 실행"""
    print("\n🔍 CBS 프로젝트 검증 시작...")
    
    validator = ProjectValidator()
    validator.generate_report()

if __name__ == "__main__":
    main()