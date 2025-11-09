{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "my-package-dev-env";

  buildInputs = [
    pkgs.python3
    pkgs.python3Packages.virtualenv
    pkgs.python3Packages.build
    pkgs.python3Packages.twine
  ];

  shellHook = ''
    echo Entering pure nix-shell...
    export PYTHONPATH=
    export PATH=$PWD/.venv/bin:$PATH
    virtualenv .venv
    source .venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -e .  # install your package in editable mode
  '';
}

