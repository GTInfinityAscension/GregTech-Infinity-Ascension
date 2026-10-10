{
  description = "GregTech Infinity Ascension modpack";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pack = builtins.fromTOML (builtins.readFile ./pack.toml);
        # Builds run tools/release.py; neither output needs the network (mods are referenced, not downloaded).
        release = kind: pkgs.stdenvNoCC.mkDerivation {
          pname = "gregtech-infinity-ascension-${kind}";
          inherit (pack) version;
          src = ./.;
          nativeBuildInputs = with pkgs; [ packwiz python3 ];
          dontFixup = true;
          buildPhase = ''
            export HOME=$TMPDIR
            python3 tools/release.py ${kind} out
          '';
          installPhase = ''
            mkdir -p $out
            cp out/*.zip $out/
          '';
        };
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [ packwiz python3 jdk17 yq ];
        };
        packages = {
          curseforge = release "curseforge";
          server = release "server";
          default = release "curseforge";
        };
      });
}
