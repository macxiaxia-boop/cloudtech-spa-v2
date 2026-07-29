
"""
云数科技 CloudTech v2.0.0
AI数字营销中台 — 23工具·6引擎
"""
import sys, os

def main():
    print("=" * 50)
    print(f"  云数科技 CloudTech v2.0.0")
    print("  AI数字营销中台 — 23工具·6引擎")
    print("=" * 50)
    print()
    print("  启动选项:")
    print("    1. 打开 Web 管理后台")
    print("    2. 启动 AI 内容生产管线")
    print("    3. 启动数据分析引擎")
    print("    4. 启动 Streamlit 仪表盘")
    print("    5. 查看系统状态")
    print("    q. 退出")
    print()

    while True:
        choice = input("  请选择 (1-5/q) > ").strip()

        if choice == "1":
            print("  启动管理后台 http://localhost:5001/admin ...")
            from admin_dashboard import app
            app.run(host="0.0.0.0", port=5001, debug=False)
        elif choice == "2":
            print("  启动内容生产管线...")
            os.system("python " + os.path.join(os.path.dirname(__file__), "content-pipeline.ps1"))
        elif choice == "3":
            print("  启动数据分析引擎...")
            os.system("python " + os.path.join(os.path.dirname(__file__), "data_analysis_engine.py --interactive"))
        elif choice == "4":
            print("  启动仪表盘 http://localhost:8501 ...")
            os.system("streamlit run " + os.path.join(os.path.dirname(__file__), "..", "dashboard", "streamlit_app.py") + " --server.port 8501")
        elif choice == "5":
            from system_health_monitor import SystemHealthMonitor
            monitor = SystemHealthMonitor()
            report = monitor.run_full_check()
            print(report)
        elif choice.lower() == "q":
            print("  再见！")
            break
        else:
            print("  无效选项")

if __name__ == "__main__":
    main()
