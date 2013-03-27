#!/bin/bash
#

tool='/root/gits-huangzx/ybs/package-report'
gitdir='/root/gits-huangzx/package-report'
log='package-report.log'

cd $gitdir
$tool >$log
if grep -q "more than" $log; then
    git add * -A
    git commit -am "Report at $(date)"
    git push   
fi
