# pres et objectif 
Je fais ca pour la these, en gros j'aimerai montrer mes competences pour appuyer ma candidature

pour cela j'ai deja un petit env de rugbyHRL qui me permet de tester dans un premier temps des algos de ppo classique et dans un second temps peut etre essayer trois trucs : 
- curriculum 
- feudal ou hiro 
- et DIAYN ? 

Donc le ppo ne porte pas reelllement ses fruits pour l'instant le18 avril. on remarque que la reward reste toujours capé vers -55 en gros que le model n'a pas de signe clair de reward, donc de bonne action, le reward shaping n'a pour l'instant pas trop aide, un peu de curriculum permettrait d'avoir surement des meilleurs resultats 

J'aimerai dans un premier savoir sur lequel des algos me focus plus, curriculum me permettrait d'avoir plus de resultats concret  mais met moins en avant les techs de l'etat de l'art. ou utiliser diayn qui est utilise actuellement sur le robot foot. et feudal et hiro semble plus simple a impl. mais est plus technique et peut etre s'eloigne des objectifs de la these ou en tout cas de l'offre. 

Si je devais prioritiser je pense que partir sur notre ppo qui marche pas comme exemple peut etre interessant, quand emme un peu ameliorer le reward shapping. 


Bon du coup j'ai continuer d'entrainer en ppo avec du reward shapping, je pense que les porchaines etapes sont d'utiliser le curriculum

# todo : 
## Curriculum : 
- [x] faire en sorte d'avoir un reset plus configurable pour avoir du curriculum 
- [x] refaire un jupyter notebook 

## Essayer DIAYN 
Je pense on peut essayer diayn on a que trois action ou deux á voir si ca donne de meilleurs resultats 

## Essayer feudal 
Mais j'ai peur de pas avoir le temps  laissons nous focus sur curriculumn et diayn pour l'instant 

 