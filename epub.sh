#!/opt/local/bin/bash -

shopt -s nullglob
shopt -s extglob

cd "$(dirname "$0")"
if [ ! -f rsa.key ]; then
    exit 1
fi

mkdir -p books
cd books

for bookzip in *.zip; do
    book="$(basename "$bookzip" .zip)"

    if [ ! -d "$book" ]; then
        mkdir -p "$book"
        unzip "$bookzip" -d "$book"
        rm "$bookzip"
    fi

    if [ ! -f "$book"/META-INF/encryption.xml ]; then
        continue
    fi
    pushd "$book"

    ek="$(xmllint META-INF/encryption.xml --xpath '//*[local-name()="CipherValue"]/text()' | base64 -d | openssl rsautl -decrypt -inkey ../../rsa.key | xxd -p)"

    for file in $(xmllint META-INF/encryption.xml --xpath '//*[local-name()="CipherReference"]/@URI' | sed -E -e 's/ +URI="([^"]+)"/\1 /g'); do
        file=$(printf '%b' "${file//%/\\x}")
        echo ... "$file"
        iv="$(head -c16 "$file" | xxd -p)"
        tail -c+17 "$file" | openssl enc -aes128 -d -K "$ek" -iv "$iv" -out "$file".plain
        mv "$file".plain "$file"
    done

    rm META-INF/encryption.xml
    zip -9 -X -r ../"$book".epub mimetype !(mimetype)
    popd
done
