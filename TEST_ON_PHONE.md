# Tester AdReceipts sur votre téléphone Xiaomi

Ce guide est pour vous, sur **votre propre téléphone**, pas à pas. Rien n'a encore été testé sur un vrai téléphone : vous êtes le premier test. Prenez votre temps. À chaque étape, il y a ce qu'il faut faire si quelque chose ne va pas, et quand **s'arrêter**.

Règle générale : si vous avez un doute, arrêtez-vous. Tant que vous n'avez pas lancé `apply --execute`, rien n'a changé sur le téléphone (à part le petit test de l'étape 5, qui se défait tout seul).

---

## 1. Sauvegarder photos et données

**À faire :**
- Sauvegardez vos photos et vidéos (sur un ordinateur, ou dans le cloud de votre choix).
- Vérifiez que vos contacts sont synchronisés avec votre compte.
- Notez vos applications bancaires et de paiement, et vérifiez que vous savez vous y reconnecter (identifiants, codes).
- Chargez le téléphone à plus de 50 %.

**Si ça ne va pas :** si une sauvegarde échoue, ne continuez pas. Réglez d'abord la sauvegarde.

## 2. Installer platform-tools (adb) sur l'ordinateur

**À faire :**
1. Téléchargez « SDK Platform-Tools » pour Windows depuis le site officiel Android : https://developer.android.com/tools/releases/platform-tools
2. Décompressez le dossier, par exemple dans `C:\platform-tools`.
3. Ouvrez un terminal (PowerShell) et tapez : `C:\platform-tools\adb.exe version`. Une version doit s'afficher.
4. Installez Python 3.9 ou plus récent si ce n'est pas déjà fait (`python --version`).

Si adb n'est pas dans le PATH, ajoutez `--adb C:\platform-tools\adb.exe` à chaque commande, ou une fois pour toutes : `$env:ADRECEIPTS_ADB = "C:\platform-tools\adb.exe"` dans PowerShell.

**Si ça ne va pas :** « adb n'est pas reconnu » veut dire que le chemin est faux : utilisez le chemin complet ci-dessus.

## 3. Activer le débogage USB

**À faire sur le téléphone :**
1. Paramètres > À propos du téléphone > touchez plusieurs fois « Version de l'OS » jusqu'au message « Vous êtes maintenant développeur ».
2. Paramètres > Paramètres supplémentaires > Options pour les développeurs > activez **Débogage USB**.
3. Branchez le câble USB. Sur le téléphone, acceptez « Autoriser le débogage USB ? » (cochez « Toujours autoriser depuis cet ordinateur » si c'est votre ordinateur).

Xiaomi a aussi un interrupteur séparé « Débogage USB (paramètres de sécurité) ». **Ne l'activez pas pour l'instant.** Il n'est utile que si une étape plus loin échoue avec une erreur de permission ; il demande un compte Xiaomi.

**Si ça ne va pas :** si le téléphone ne propose pas l'autorisation, changez de câble (certains câbles ne font que charger), choisissez le mode « Transfert de fichiers » dans la notification USB, puis débranchez et rebranchez.

## 4. `doctor` puis `scan` : rien n'est modifié

**À faire :**
```text
python adreceipts.py doctor
python adreceipts.py scan
```
Ouvrez le rapport `scan.html` indiqué à la fin. Il liste les emplacements de pub connus, ce qui a été trouvé, et ce qui n'a pas été vérifié. Le rapport signalera que HyperOS 3 n'est pas encore décrit par les sources du catalogue : c'est normal.

**Si ça ne va pas :**
- « No phone is connected » / « not authorized » : refaites l'étape 3.
- « work profile » ou « managed » : **arrêtez-vous**. AdReceipts ne touche pas aux téléphones gérés.
- Toute autre erreur : notez le message et arrêtez-vous ; rien n'a été modifié.

Vous pouvez vous arrêter ici : rien n'a changé.

## 5. `backup` puis `drill`, et vérifier sur le téléphone

**À faire :**
```text
python adreceipts.py backup
python adreceipts.py drill
```
Le « drill » désactive un paquet sans importance (par exemple l'easter egg Android), vérifie, puis le réactive et vérifie encore. Ensuite, sur le téléphone : le téléphone fonctionne comme avant, l'écran d'accueil s'affiche.

Notez l'emplacement des scripts `restore-standalone.cmd` et `.sh` affiché par `backup`.

**Si ça ne va pas :**
- « No harmless package » : **arrêtez-vous** ; utilisez AdReceipts uniquement en mode scan.
- « Undo did not work » : réactivez le paquet indiqué à la main (Paramètres > Applications > Gérer les applications > menu > afficher les applications système > le paquet > Activer), puis **arrêtez-vous** et notez ce qui s'est passé dans le rapport de l'étape 10.

## 6. Un petit lot sûr, puis appels, SMS, notifications et paiement

**À faire :**
```text
python adreceipts.py plan
python adreceipts.py plan --select pkg:com.miui.analytics --approve
python adreceipts.py apply
python adreceipts.py apply --execute
```
Choisissez un seul élément « safe » pour commencer (l'exemple ci-dessus en est un, s'il apparaît dans votre plan). Le premier `apply` est un essai à blanc : il montre la commande sans rien changer.

Puis vérifiez à la main :
- passer un appel et en recevoir un ;
- envoyer et recevoir un SMS ;
- recevoir une notification (par exemple un message) ;
- ouvrir votre application bancaire et de paiement (et le paiement sans contact si vous l'utilisez).

Enregistrez ce qui marche : `python adreceipts.py verify --confirmed calls sms notifications payments` (gardez seulement ce qui marche).

**Si ça ne va pas :** passez directement à l'étape 7 pour tout défaire. Si `apply` s'arrête tout seul, il a déjà défait le lot en cours : lisez le message.

## 7. Défaire ce lot et vérifier qu'il est revenu

**À faire :**
```text
python adreceipts.py restore --all
python adreceipts.py recheck
```
Sur le téléphone, vérifiez que l'application concernée est de nouveau activée (Paramètres > Applications > Gérer les applications > afficher les applications système).

**Si ça ne va pas :** lancez le script `restore-standalone.cmd` du dossier du run. Sinon, réactivez à la main comme à l'étape 5. Si quelque chose reste désactivé, **arrêtez-vous** et notez-le.

## 8. Appliquer le plan choisi et tout revérifier

**À faire :**
1. `python adreceipts.py plan` : relisez chaque élément, son risque et ses effets. Faites aussi, à la main, les réglages de la section « Switches to turn off by hand » (Sécurité, Nettoyeur, Thèmes, Téléchargements, Musique, Vidéo, Navigateur, tiroir d'applications...).
2. `python adreceipts.py plan --select <ID> <ID> ... --approve` (ajoutez `--dns adguard` seulement si vous voulez le filtrage DNS ; le fournisseur voit alors les noms de domaine consultés).
3. `python adreceipts.py apply`, puis `python adreceipts.py apply --execute`.
4. Revérifiez appels, SMS, notifications, banque et paiement, puis `python adreceipts.py verify --confirmed ...`.

**Si ça ne va pas :** `python adreceipts.py restore --batch <numéro>` pour le lot en cause, ou `restore --all` pour tout. Si un message dit que le fabricant bloque un changement, ne forcez pas : AdReceipts ne change jamais de méthode tout seul.

## 9. Générer les reçus et relire les images avant tout partage

**À faire :**
```text
python adreceipts.py receipts
```
Facultatif, si vous acceptez les captures d'écran (elles restent sur l'ordinateur) : lancez d'abord `scan --screenshots --consent` au début d'un nouveau run, puis `receipts --screenshots --consent` à la fin.

Avant de partager quoi que ce soit :
```text
python adreceipts.py share
```
Regardez chaque fichier du dossier `share-...`. N'ajoutez les images (`share --include-images`, qui demande Pillow) qu'après les avoir toutes regardées : pas de nom de compte, pas de notification, rien de personnel.

**Si ça ne va pas :** en cas de doute sur une image, ne la partagez pas.

## 10. Remplir le rapport d'appareil

**À faire :** copiez `catalog/reports/TEMPLATE.md` en `catalog/reports/xiaomi-<modele>-<date>.md` et remplissez-le : version du système, ce qui a été changé, ce qui marchait après, ce qui a été restauré. Pas de numéro de série, d'IMEI, de nom de compte ni de numéro de téléphone.

Ensuite, suivez la liste de `LAUNCH.md` pour mettre à jour le README et le catalogue avec les vrais résultats.

**Pour finir :** désactivez le débogage USB (Options pour les développeurs > Débogage USB).
