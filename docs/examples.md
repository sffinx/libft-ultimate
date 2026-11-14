# Exemples de résultats

Ces extraits viennent d’exécutions du testeur sur sa bibliothèque de
contrôle, avec et sans défaut volontaire. Ils ne sont pas des résultats
de la Moulinette ni la validation d’un projet étudiant.

## Une fonction réussie

```sh
./libft-test ../libft --only strlen
```

```text
  OK      ft_strlen             66/66
Portée : fonctions sélectionnées uniquement ; aucun bilan complet du projet.
```

Les autres fonctions ne sont pas testées par cette commande. Le nombre
de cas dépend de la révision et de la graine utilisées.

## Une longueur incorrecte

Le défaut de démonstration ajoute 1 à chaque résultat de `ft_strlen`.
L’entrée contient sept octets avant le NUL ; le programme en annonce huit.

```text
  ft_strlen — 'Hello !'
    longueur en octets ; attendu=7 ; obtenu=8
    Cas : strlen.05d9976b8b0e
    Référence : entrée publique adaptée au contrat PDF 1.3.
    Les contrôles mémoire et le diagnostic sont ajoutés par Ultimate.
    0x050f/libft-war-machine : https://github.com/0x050f/libft-war-machine/blob/c344fdf251db4aea6585e1522d3d22632aefc806/tests/Part1_functions/ft_strlen/main.c#L36
    jtoty/Libftest : https://github.com/jtoty/Libftest/blob/d6cdc5255fc1aacaa19dca07d8adab0ca65e9bdb/tests/Part1_functions/ft_strlen/main.c#L36
```

Les liens indiquent l’origine de l’entrée. Les contrôles du moteur et les
messages peuvent différer du testeur cité.

## Un échec d’allocation

```sh
./libft-test ../libft --only split,lstmap
```

Les scénarios d’échec font rater chaque allocation observée, à son tour.
Ils vérifient le retour et la libération des blocs déjà créés. Une fuite
indique le nombre de blocs et d’octets encore vivants à la fin du cas.

Un scénario sans référence publique est affiché comme `test ajouté`.

## Un doute sur une erreur

Relancer la fonction avec les mêmes options et la même graine :

```sh
./libft-test ../libft --only split --seed 42 --valgrind \
  --json /tmp/libft-split.json
```

Comparer l’entrée et le résultat attendu au sujet PDF 1.3 ou au manuel.
Si le diagnostic paraît incorrect, joindre l’identifiant du cas et un
exemple minimal à une [issue](https://github.com/sffinx/libft-ultimate/issues/new/choose).

Le résultat d’un autre testeur est utile pour comparer. Il ne prouve pas
à lui seul que le code ou ce testeur a raison.
