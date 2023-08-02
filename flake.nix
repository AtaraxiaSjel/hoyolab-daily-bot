{
  description = "Hoyolab Daily Check-in Bot.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }: let
    inherit (nixpkgs) lib;
    genSystems = lib.genAttrs [
      "x86_64-linux"
    ];
    pkgsFor = nixpkgs.legacyPackages;
  in {
    overlays.default = _: prev: {
      hoyolab-daily-bot = prev.callPackage ./default.nix {
        version = "1.1";
      };
    };
    packages = genSystems (system:
      (self.overlays.default null pkgsFor.${system})
      // {
        default = self.packages.${system}.hoyolab-daily-bot;
      });
  };

  nixConfig = {
    extra-substituters = ["https://ataraxiadev-foss.cachix.org"];
    extra-trusted-public-keys = ["ataraxiadev-foss.cachix.org-1:ws/jmPRUF5R8TkirnV1b525lP9F/uTBsz2KraV61058="];
  };
}