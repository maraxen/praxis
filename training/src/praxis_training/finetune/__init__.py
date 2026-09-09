"""P2.6 fine-tune lane (D5 recipe): pre-registered negative-mixing ablation.

Modules stay import-light: ``mixing`` and ``versions`` never touch torch;
``render`` needs only the tokenizer; ``train`` performs the heavy imports
inside functions so ``import praxis_training.finetune`` is always cheap.
"""
