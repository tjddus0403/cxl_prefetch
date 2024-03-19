# cxl_prefetch
## Datasets
- From ChampSim for the ML Prefetching Competition at [https://github.com/Quangmire/ChampSim](https://github.com/Quangmire/ChampSim)
- sim/traces/trans/ 파일들을 이용하여 다음과 같은 순서로 변환
  - ~ 실행하여 .vaddr 추출
  - v2p.ipynb 실행하여 .paddr 추출
  - leap simulator로 paddr 실행하여 miss에 대한 .cstate 추출
  - clstm/20201786.ipynb 파일 내부에서 Recreate Train Dataset 실행하여 .csv 생성
  - **Final dataset** : .csv 
## Development Environment
<p align="center">
  <img src="https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white"/></a>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/></a>
</p>

*OS :* Ubuntu 20.04  
*Framework :* Pytorch 1.7.1+cu110  
*Language :* Python3.9.13  
