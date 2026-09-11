# Support dataset

Questa cartella ospita gli anagrafiche / support dataset usati dai dataset
principali in `datasets/`.

## Regole

- un support dataset e' una directory con `dataset.yml` + `sql/`, come i dataset
  principali
- si esegue con `make run` (prima dei dataset principali)
- si dichiara nei `mart` o nei `clean` dei dataset che lo consumano
- quando un support dataset e' condiviso tra piu' repo del Lab, si valuta di
  spostarlo in un repo dedicato o in `dataset-incubator` (issue upstream)
