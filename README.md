# Mobility Web Interface (Internship Project)

**This project is a web-based frontend for the [Mobility](https://github.com/mobility-team/mobility) Python package.**

It was developed during an **internship at [AREP](https://arep.fr)** to provide a user-friendly interface for visualizing mobility models, generating transport zones, and analyzing modal splits.

🚀 **Live Demo:** [https://mobility.cavydev.com](https://mobility.cavydev.com)

---

## ⚠️ Important Note Regarding Data (Live Demo)

The `mobility` engine is a powerful simulation tool that requires significant computational resources (RAM/CPU) and downloads large OpenStreetMap datasets to generate precise travel models.

**For this hosted demonstration:**

- The data you see (travel times, modal shares) is **randomly sampled/pre-baked**.
- We opted for this lightweight approach because running the full simulation stack requires more memory than available in standard containerized hosting environments, often leading to instability.

**This interface is fully capable of running the real `mobility` engine** when deployed on appropriate infrastructure (local workstations or high-memory servers).

---

## Project Architecture

- **Frontend/App:** Python Dash application (located in `front/`).
- **Engine:** [Mobility](https://github.com/mobility-team/mobility) (installed as a dependency).
- **Deployment:** Docker & Traefik.

---

# About the Mobility Library (Underlying Engine)

*The following is the original description of the core Mobility library used by this project.*

**Mobility** is an open source Python library for modelling the travel behavior of local populations, from short range to long range trips, for different travel motives (personnal and professional) and on multimodal transport networks (walk, bicycle, public transport and car). It can be used on regions composed of hundreds of cities (up to a thousand), located in France and Switzerland.

It provides estimated travel diaries of a local sample population, based on indidividual socio-economical characteristics, expected daily activity programmes, competition over opportunities at places of interest (jobs, shops, leisure facilities...) and congestion of transport infrastructures.

It uses discrete choice models to evaluate destination and mode decisions based on generalized cost estimates, estimated from detailed unimodal and intermodal travel costs between the transport zones of the studied region.

It handles the preparation of most inputs from open data (administrative boundaries, housing and places of interest spatial distribution, transport infrastructure, public transport schedules, activity programmes) and provides reasonable default values for model parameters.

<img width="305" height="256" alt="Flow map of Bayonne region" src="https://github.com/user-attachments/assets/629e5ed0-aa5a-4949-acc6-60615e8f31b5" />
<img width="305" height="256" alt="Car modal share of Bayonne region" src="https://github.com/user-attachments/assets/9fb95b35-4443-40d0-8640-ce1c9846d83b" />

To see how Mobility works, take a look at the [installation instructions](docs/source/installation.md) and the [quickstart page](docs/source/quickstart.md). If you want to contribute, see our [guidelines](docs/contributing.md) and the [issue tracker](https://github.com/mobility-team/mobility).

Mobility has been developed mainly by [AREP](https://arep.fr) and [Elioth](https://elioth.com/) with [ADEME](https://wiki.resilience-territoire.ademe.fr/wiki/Mobility) support, but anyone can join us!
For now, it is mainly focused on French and Swiss territories.

[Documentation on mobility.readthedocs.io](https://mobility.readthedocs.io/en/latest/)

Find more infos (in French) on [Mobility website](https://mobility-team.github.io/)

# Mobility, une librairie open source pour la modélisation de la mobilité

Mobility est une librairie Python open source servant à calculer l'empreinte carbone liée à la mobilité d'une population locale.

L'outil est principalement développé par [AREP](https://arep.fr) et [Elioth](https://elioth.com/) avec le soutien de l'[ADEME](https://wiki.resilience-territoire.ademe.fr/wiki/Mobility), mais toute personne peut nous rejoindre !
Pour l'instant, la solution est centrée sur les territoires et les données françaises.

[Documentation sur mobility.readthedocs.io](https://mobility.readthedocs.io/en/latest/)

Plus d'infos sur [le site web](https://mobility-team.github.io/) !

# Contributeur·ices

| Entreprise/école  | Participant·es |
| :------------- | :------------- |
| AREP  | Capucine-Marin Dubroca-Voisin <br> Antoine Gauchot <br> Félix Pouchain |
| Elioth  | Louise Gontier <br> Arthur Haulon  |
| École Centrale de Lyon | Anas Lahmar <br> Ayoub Foundou <br> Charles Pequignot <br> Lyes Kaya  <br> Zakariaa El Mhassani |
| École nationale des sciences géographiques (ENSG) | 2025 : <br> Anaïs Floch <br> Liam Longfier <br> Gabin Potel <br> 2024 : <br> Marta Ducamp <br> Joanna Gosse <br> Baptiste Delaunay <br> Tony Thuillard

# Utilisations

| Utilisateur  | Date | Projet |
| :------------- | :------------- | :------------- |
| AREP  | 2020-2022 | [Luxembourg in Transition]([url](https://www.arep.fr/nos-projets/luxembourg-in-transition-paysage-capital/)) |
| AREP | 2022 | Étude pour le [Grand Annecy]([url](https://www.arep.fr/nos-projets/grand-annecy/)) |
| AREP | 2024 | Étude de potentiel pour la réouverture de la gare de Bidart |
| AREP | 2024-en cours | Décarbonation des mobilités le Grand Genève, avec la Fondation Modus |

# Comment contribuer ?

* Vous pouvez regarder nos [issues](https://github.com/mobility-team/mobility/issues), particulièrement celles marquées comme [good-first-issue](https://github.com/mobility-team/mobility/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22), et proposer d'y contribuer.
- Tester l'outil et nous indiquer là où la documentation peut être améliorée est très utile ! Que ce soit pour une suggestion ou une issue, n'hésitez pas à [ouvrir une issue](https://github.com/mobility-team/mobility/issues/new).
- Nous espérons que vous pourrez utiliser Mobility pour vos travaux de recherche et de conseil ! Nous comptons sur vous pour partager le code que vous avez utilisé.
- Nous suivons PEP8 pour notre code Python. Pour d'autres bonnes pratiques, [suivez le guide](https://github.com/mobility-team/mobility/tree/main/mobility) !
