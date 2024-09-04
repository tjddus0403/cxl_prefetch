#!/bin/sh

ROOT="./paddr/2MB/"
INPUT="$ROOT$1/$1_5m.paddr"
echo "$INPUT"
echo `head -4000000 $INPUT > $ROOT$1/$1_4m_64.paddr`
echo `head -3000000 $INPUT > $ROOT$1/$1_3m_64.paddr`
echo `tail -1000000 $INPUT > $ROOT$1/$1_1m_tail_64.paddr`