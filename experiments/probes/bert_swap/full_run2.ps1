Set-Location C:\Users\muzaf\PycharmProjects\contextDecayWindow
$S = 'experiments/probes/bert_swap/bert_swap_stream.py'
python $S --model prajjwal1/bert-small --id opt2_small --mode retrain --epochs 2 *> experiments/probes/bert_swap/runs/opt2_small.log
python $S --model bert-base-uncased --id opt2_base --mode retrain --epochs 2 *> experiments/probes/bert_swap/runs/opt2_base.log
New-Item -ItemType File -Force experiments/probes/bert_swap/runs/OPT2_DONE.txt | Out-Null
