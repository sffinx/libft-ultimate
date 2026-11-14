# Fusion, couverture et limites

Sujet de référence : PDF Libft v1.3, fourni localement.
Version du testeur : 0.1.0. Relevé du 14 novembre 2026.

## Ce qui est effectivement fusionné

1431 occurrences d’entrées publiques ont été ramenées à
932 jeux d’entrées distincts, avec leurs origines regroupées.
Le catalogue final contient 6765 cas distincts pour les 43 fonctions.
Les scénarios générés complètent les entrées extraites : domaine complet
des caractères, classes de limites, données binaires, alignements,
pages de garde, chevauchements, callbacks, échecs malloc et nettoyage.

Les sources étudiées sont les 14 projets de [CREDITS.md](../CREDITS.md). Les
agrégateurs Supreme et francinette-image n’ajoutent pas à eux seuls une
nouvelle origine fonctionnelle. Les suites embarquées ne sont pas exécutées
en cascade : il n’y a qu’un moteur et qu’un catalogue.

Les références d’une entrée importée sont précises : dépôt, révision,
fichier et ligne. Les attentes sont recalculées à partir du contrat 1.3.
La priorité de Tripouille concerne l’ordre des références et des cas ;
elle ne change pas les résultats attendus ni le niveau d’exigence.

## Déduplication

La clé comprend fonction, octets d’entrée, paramètres, résultat attendu,
disposition des gardes et politique d’injection. Le libellé et le nombre
de testeurs d’origine ne créent pas un nouveau test. Les valeurs converties
en unsigned/char sont normalisées lors de l’adaptation.

Deux entrées différentes avec le même résultat ne sont pas nécessairement
des doublons : elles peuvent déclencher deux branches différentes. Une
garde avant et une garde après ne contrôlent pas le même accès. Un échec
d’allocation constitue un autre scénario qu’une allocation réussie.

## Origines et réécriture

Les entrées publiques sont dans `.testeur/corpus.json`. Les sources/révisions et les
empreintes des archives sont dans `.testeur/sources.json`. L’inventaire traçable
des appels rencontrés se trouve dans `.testeur/audit-sources.json`.

La collecte ne transforme pas arbitrairement du C en Python. Elle accepte
les constantes, les arguments littéraux, des opérations entières bornées,
des wrappers identifiés de Francinette et les tables identifiées de ylam21.
Les appels dépendant de variables/du contrôle de flot ne sont pas importés
automatiquement. Leurs familles de scénarios ont servi à la revue et à
l’écriture des contrôles génériques. Ce n’est pas une preuve d’équivalence
assertion par assertion avec tous les programmes historiques.

L’inventaire conserve 876 occurrences non importées directement
(déclarations, expressions non résolues ou entrées écartées). Elles ne
sont pas comptées comme tests repris. Les anciens tests hors des 43
fonctions et les répertoires des autres projets ne font pas partie du scan.

Un échec dû à une garde ou à Valgrind est un contrôle ajouté par le
nouveau moteur, même lorsque l’entrée possède une référence publique.
La sortie et le JSON évitent d’affirmer que le testeur d’origine donne
exactement le même diagnostic.

## Décisions pour éviter les faux positifs

- Classification : résultat exact 0/1 selon le PDF, domaine unsigned char
  et EOF ; isascii reçoit aussi des valeurs entières hors ASCII.
- Comparaisons : signe de memcmp/strncmp uniquement, pas une différence
  numérique arbitrairement copiée depuis une libc.
- Atoi : valeurs représentables par int seulement ; dépassements exclus.
- NULL hors contrat : exclus. Liste vide et contenu de nœud NULL : inclus.
- Le résultat NULL d’un callback lstmap peut être un contenu valide ; il
  n’est pas assimilé automatiquement à un échec malloc du testeur.
- Tailles allouées : au moins la place utilisée, pas un nombre exact
  d’octets ou d’appels malloc exigé sans fondement dans le sujet.
- Injection : chaque allocation observée sur un scénario choisi échoue
  à son tour. Les allocations propres aux callbacks sont séparées.
- Pas de seuil de benchmark relatif à la libc. Un timeout est indiqué
  comme un résultat à examiner, avec un délai configurable.
- Pas de conversion silencieuse des anciennes listes bonus en option.
- Les capacités fictives SIZE_MAX pour un petit tableau de destination
  ne sont pas utilisées comme oracle de conformité pour strlcpy/strlcat.
- Les appels indirects et les variantes de Makefile non reconnues sont
  signalés pour revue, pas déclarés faux par simple motif textuel.

## Couverture par fonction

| Fonction | Cas distincts |
|---|---:|
| ft_isalpha | 257 |
| ft_isdigit | 257 |
| ft_isalnum | 257 |
| ft_isascii | 267 |
| ft_isprint | 257 |
| ft_strlen | 66 |
| ft_memset | 520 |
| ft_bzero | 104 |
| ft_memcpy | 104 |
| ft_memmove | 98 |
| ft_strlcpy | 65 |
| ft_strlcat | 260 |
| ft_toupper | 257 |
| ft_tolower | 257 |
| ft_strchr | 208 |
| ft_strrchr | 202 |
| ft_strncmp | 549 |
| ft_memchr | 130 |
| ft_memcmp | 72 |
| ft_strnstr | 564 |
| ft_atoi | 528 |
| ft_calloc | 50 |
| ft_strdup | 66 |
| ft_substr | 309 |
| ft_strjoin | 121 |
| ft_strtrim | 146 |
| ft_split | 218 |
| ft_itoa | 85 |
| ft_strmapi | 34 |
| ft_striteri | 33 |
| ft_putchar_fd | 260 |
| ft_putstr_fd | 28 |
| ft_putendl_fd | 27 |
| ft_putnbr_fd | 67 |
| ft_lstnew | 3 |
| ft_lstadd_front | 5 |
| ft_lstsize | 5 |
| ft_lstlast | 5 |
| ft_lstadd_back | 5 |
| ft_lstdelone | 2 |
| ft_lstclear | 6 |
| ft_lstiter | 5 |
| ft_lstmap | 6 |

## Limites techniques

- Linux 64 bits et GNU-compatible --wrap. Pas de validation macOS.
- Les compilations et commandes make tournent dans une copie. Ce n’est
  pas une sandbox de sécurité contre des scripts malveillants.
- Un enfant par cas, arrêt au premier défaut dans ce cas ; les cas
  suivants continuent. Une erreur peut en masquer une autre dans le même
  scénario, comme dans les testeurs classiques.
- Sentinelles sur allocations et pages protégées pour les entrées.
  Les lectures de padding et les accès après free demandent Valgrind.
- Le suivi interne borne une allocation à 64 Mio et le nombre de blocs
  simultanément enregistrés à 60 000. Les scénarios normaux sont bien
  en dessous. Ce testeur n’est pas un stress test de toute la RAM.
- Les signatures sont contrôlées séparément du moteur. Une signature
  erronée reste un échec même si les valeurs d’exécution coïncident.
- Les vérifications de README, de fichiers inutiles et de tous les appels
  transitifs permis par fonction ne sont pas intégralement automatisées.
- Pas de score ni de simulation annoncée de la Moulinette.

## Compléter sans gonfler la suite

Pour ajouter un cas : rattacher une référence exacte ou écrire « ajouté »,
vérifier son domaine dans le PDF/man local, créer son oracle, puis ajouter
une mutation démontrant qu’il détecte le défaut visé sans rejeter une
variante valide. Le contrôle des identifiants empêche les doublons exacts.
