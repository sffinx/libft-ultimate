# Contribuer

Les premiers retours recherchés concernent les faux positifs, les plantages
du testeur et les erreurs difficiles à comprendre.

## Ouvrir une issue

Indiquer :

- la sortie de `./libft-test --version` ;
- la distribution et les versions de Python, du compilateur et de Valgrind ;
- la commande et la graine utilisées ;
- l’identifiant du cas, le message complet et le résultat attendu ;
- un exemple assez petit pour reproduire le problème.

Pour contester un résultat, citer le passage du sujet PDF 1.3 ou la page
du manuel. Le résultat d’un autre testeur peut aider à comparer, mais ne
remplace pas le contrat de la fonction.

Ne pas joindre tout son dépôt de rendu ou le PDF du sujet. Un extrait
minimal, des entrées et le diagnostic suffisent généralement.

## Proposer un changement

Garder une pull request centrée sur un problème. Décrire ce qui échouait,
ce qui est attendu après la correction et la vérification effectuée.

Un nouveau cas doit avoir une origine : lien vers le fichier et la révision
du testeur consulté, ou mention « test ajouté ». Vérifier qu’il ne répète
pas un cas existant. Un échec d’allocation ou une autre disposition mémoire
peut justifier un cas distinct.

Pour une correction du moteur, ajouter une petite bibliothèque volontairement
défectueuse qui reproduit le problème, puis vérifier qu’une variante valide
continue à passer. Éviter de tester un comportement que le sujet laisse libre.

## Vérifier le testeur

Sur Linux 64 bits, avec Python 3.10+, un compilateur C, Make, binutils et
Valgrind :

```sh
python3 .testeur/tests/selftest.py /tmp/libft-selftest.json
python3 .testeur/tests/test_cli.py
python3 .testeur/tests/test_publication.py
```

La bibliothèque de contrôle est dans `.testeur/tests/fixture.c`.
Elle utilise volontairement la libc : elle sert à tester le moteur,
pas à fournir une Libft à rendre.

Le workflow GitHub Actions exécute ces commandes. Les fichiers de travail
et les rapports locaux ne doivent pas être ajoutés au dépôt.

## Reprendre du code tiers

Vérifier la licence avant de reprendre du code. Un crédit ne remplace pas
une autorisation. Conserver les notices applicables et mettre à jour
[CREDITS.md](CREDITS.md). La licence MIT du projet couvre son code original ;
elle ne change pas les droits des auteurs des projets cités.
