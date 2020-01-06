#!/opt/local/bin/bash -

if [ ! -f rsa.pem ]; then
    sqlite3 ~/Library/Application\ Support/Readmoo/Local\ Storage/app_readmoo_0.localstorage 'SELECT value FROM itemtable WHERE key = "rsa_privateKey";' >rsa.pem
fi

mkdir -p books
cd books

for bookzip in ~/Library/Containers/com.readmoo.readmoodesktop/Readmoo/api/book/*; do
    book="$(basename "$bookzip" .zip)"

    if [ ! -d "$book" ]; then
        mkdir -p "$book"
        unzip "$bookzip" -d "$book"
    fi

    if [ ! -f "$book"/META-INF/encryption.xml ]; then
        continue
    fi
    pushd "$book"

    ek="$(xmllint META-INF/encryption.xml --xpath '//*[local-name()="CipherValue"]/text()' | base64 -d | openssl rsautl -decrypt -inkey ../../rsa.pem | xxd -p)"

    for file in $(xmllint META-INF/encryption.xml --xpath '//*[local-name()="CipherReference"]/@URI' | sed -E -e 's/ +URI="([^"]+)"/\1 /g'); do
        iv="$(head -c16 "$file" | xxd -p)"
        tail -c+17 "$file" | openssl enc -aes128 -d -K "$ek" -iv "$iv" -out "$file".plain
        mv "$file".plain "$file"
    done

    rm META-INF/encryption.xml
    zip -r ../"$book".epub *
    popd
done
