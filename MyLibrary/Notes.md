# Random notes/ideas
- VTbuild should accept passing `--inc_dir` as arguments.
- generate_io: if "," is in script call arguments than do not add a "," to the last generated IO.
- instantiate: generate wires when automatically passed to ports.
- mmio: r_data should have biggest register size width. address should have width = log_2(biggest register address).