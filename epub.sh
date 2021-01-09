#!/usr/local/bin/bash -

shopt -s nullglob
shopt -s extglob
shopt -s globstar

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

    ek="$(base64 -d -i ../"$book".key | openssl rsautl -decrypt -inkey ../../rsa.key | xxd -p -c 256)"

    i=0
    while true; do
        i=$((i + 1))
        xml="$(xmllint --xpath '//*[local-name()="EncryptedData"]['"$i"']' META-INF/encryption.xml 2>/dev/null)"
        [ "$xml" ] || break

        file="$(xmllint --xpath '//*[local-name()="CipherReference"]/@URI' - <<<"$xml" | sed -E -e 's/^ \w+="|"$//g')"
        file="$(printf '%b' "${file//%/\\x}")"
        method="$(xmllint --xpath '//*[local-name()="Compression"]/@Method' - <<<"$xml" | sed -E -e 's/^ \w+="|"$//g')"
        length="$(xmllint --xpath '//*[local-name()="Compression"]/@OriginalLength' - <<<"$xml" | sed -E -e 's/^ \w+="|"$//g')"

        echo ... "$file"
        iv="$(head -c16 "$file" | xxd -p)"
        tail -c+17 "$file" | openssl enc -aes256 -d -K "$ek" -iv "$iv" -nopad -out "$file".plain
        if [ "$method" -eq 8 ]; then
            cat <(printf "\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00") "$file".plain | gzip -dc >"$file" 2>/dev/null
            size="$(stat -c %s "$file")"
            if [ "$size" != "$length" ]; then
                echo "$size" != "$length"
                exit 1
            fi
        else
            head -n"$length" "$file".plain >"$file"
        fi
        rm "$file".plain
    done

    sed -E -i -e 's/ class="moofs([0-9]+|NaN) moolh([0-9]+|NaN)( non-moofont)?"//g' **/*.xhtml
    sed -E -i -e 's/ class="(([^"]+) )?moofs([0-9]+|NaN) moolh([0-9]+|NaN)( non-moofont)?"/ class="\2"/g' **/*.xhtml
    sed -E -i -e 's/<meta name="moo_white_margins" content="[^"]+"\/>//g' **/*.xhtml
    sed -E -i -e 's/<meta content="Bisheng [0-9.]+" name="moo[^"]+"\/>//' **/*.opf
    if [ -d moo_extra ]; then
        sed -E -i -e 's/<item href="\.\.\/moo_extra\/[^>]+\/>//g' **/*.opf
        rm -r moo_extra
    fi

    rm META-INF/encryption.xml
    rm ../"$book".key

    title="$(grep -Po '<dc:title( id="title")?>\K.+?(?=</dc:title>)' **/*.opf)"
    zip -9 -X -r ../"$book"."$title".epub mimetype !(mimetype)
    popd
done
