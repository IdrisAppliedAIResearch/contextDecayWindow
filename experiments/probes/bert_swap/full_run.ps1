$ErrorActionPreference = 'Continue'
Set-Location C:\Users\muzaf\PycharmProjects\contextDecayWindow
$S = 'experiments/probes/bert_swap/bert_swap_stream.py'
python $S --model prajjwal1/bert-small --id small_notrain --no-train *> experiments/probes/bert_swap/runs/small_notrain.log
python $S --model prajjwal1/bert-small --id small_train *> experiments/probes/bert_swap/runs/small_train.log
python $S --model bert-base-uncased --id base_notrain --no-train *> experiments/probes/bert_swap/runs/base_notrain.log
python $S --model bert-base-uncased --id base_train *> experiments/probes/bert_swap/runs/base_train.log
New-Item -ItemType File -Force experiments/probes/bert_swap/runs/ALL_DONE.txt | Out-Null
