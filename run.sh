mkdir -p cpprefjp
cd cpprefjp
git clone https://github.com/cpprefjp/site.git
cd site
git pull
git checkout master
cd ..

git clone https://github.com/cpprefjp/site_generator.git
cd site_generator
git pull
cd ..

git clone https://github.com/cpprefjp/kunai.git
cd kunai
git pull
cd ..

git clone https://github.com/cpprefjp/kunai_config.git
cd kunai_config
git pull
cd ..

git clone https://github.com/cpprefjp/crsearch.git
cd crsearch
git pull
cd ..

git clone https://github.com/cpprefjp/markdown_to_html.git
cd markdown_to_html
git pull
cd ..

cd ..
mkdir -p boostjp
cd boostjp
git clone https://github.com/boostjp/site.git
cd site
git pull
cd ..

cd ..
python3 stats_contribution.py $@
