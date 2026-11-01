git lfs install

git lfs track "*.fig"

git add .gitattributes

git add "docs/figmaDesign/ROVE Design.fig"

git commit -m "Track Figma file with Git LFS" || true

git lfs ls-files

git lfs push --all origin

git push origin feature/contentFromLBG
