for i in $(seq 1 20)
do
    ./upload_xml.py < Test1.xml &
    echo "uploaded ${f} $?"
done
