[Moses](https://github.com/moses-smt/mosesdecoder) comes with an [XMLPRC enabled server](https://github.com/moses-smt/mosesdecoder/tree/master/contrib/server) which is great for producting translations but does not handle pre- and postprocessing. To provide an interface similar to the [Google Translate API](https://developers.google.com/translate/) this 


How to use:
-----------

1. Start mosesserver:

```bash
/path/mosesserver -f modelpath/moses.ini
```

2. Start python server:

```bash
#!/bin/bash

SCRIPTS=/path/scripts

./server.py  -mosesurl "http://127.0.0.1:8080/RPC2" \
  -tokenizer "$SCRIPTS/tokenizer/tokenizer.perl -b -X -l de -a" \
  -truecaser  "$SCRIPTS/recaser/truecase.perl -b -model model/truecase-model.de" \
  -detokenizer "$SCRIPTS/tokenizer/detokenizer.perl -b -l en" \
  -detruecaser "$SCRIPTS/recaser/detruecase.perl -b"  \
  -tgt-tokenizer "$SCRIPTS/tokenizer/tokenizer.perl -b -X -l en -a" \
  -tgt-truecaser "$SCRIPTS/recaser/truecase.perl -b -model model/truecase-model.en" \
  -verbose 1 -port 8081 -ip 127.0.0.1 -pretty \
  -logprefix moseswrapper
```

3. Use server:

```bash
curl "http://127.0.0.1:8081/translate?q=der+Obama+kommt+nach+Oslo.&key=x&target=en&source=de"
```

```json
{
  "data": {
    "translations": [
      {
        "sourceText": "Obama kommt nach Oslo.", 
        "translatedText": "Obama comes after Oslo.", 
        "tokenization": {
          "src": [
            [
              0, 
              4
            ], 
            [
              6, 
              10
            ], 
            [
              12, 
              15
            ], 
            [
              17, 
              20
            ], 
            [
              21, 
              21
            ]
          ], 
          "tgt": [
            [
              0, 
              4
            ], 
            [
              6, 
              10
            ], 
            [
              12, 
              16
            ], 
            [
              18, 
              21
            ], 
            [
              22, 
              22
            ]
          ]
        }
      }
    ]
  }
}
```

Requirements:
-------------

* [Mosesserver](https://github.com/moses-smt/mosesdecoder/tree/master/contrib/server)
* Python 2, at least 2.7
* [CherryPy 3](http://www.cherrypy.org/)

Caveats:
--------

Be consistent with pre- and post processing steps for training and using the MT system. This server assumes the folloing order:

1. tokenization
2. truecasing (or lowercasing)
3. preprocessing (can be anything)
4. annotation (enrich input with additional information)
5. TRANSLATION
6. extraction (of additional infomation provived by mosesserver)
7. postprocessing (again, can be anything)
8. detruecasing (or realcasing)
9. detokenization

All options that specify external scripts can take multiple arguments so if your preprocessing pipeline is very different all steps can just be specified there.
