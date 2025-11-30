python3 -m pip install --upgrade pip
python3 -m pip install streamlit folium streamlit-folium pandas numpy scipy matplotlib --quiet
echo "All packages installed! Starting your hurricane app in 3 seconds..."
sleep 3
streamlit run app.py
