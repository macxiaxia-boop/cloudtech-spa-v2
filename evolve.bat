@echo off
cd /d D:\Browser\CloudTech-v2.0.0\CloudTech-Portable
D:\Python310\cpython-3.10.20-windows-x86_64-none\python.exe -c "import sys;sys.path.insert(0,'.');from self_evolution import EvolutionScheduler;r=EvolutionScheduler().evolve_from_collector();print('Evolved:',len(r.get('paradigms',[])),'paradigms',len(r.get('skills_installed',[])),'skills')" > data\evolution_auto.log 2>&1
