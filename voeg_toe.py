# -*- coding: utf-8 -*-
import json, os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bedrijven_data.json')
d = json.load(open(path, encoding='utf-8'))

nieuw = {
    'Dycore B.V.': {'wat': 'Producent van betonvloeren en prefab betonelementen voor de bouw.', 'groot': 'Middelgroot productiebedrijf.', 'dmu': 'Directeur of facility manager.', 'kans': 'Geschat 3-5 printers | Kans: Midden - bouwbedrijf met kantoor en tekenkamer.'},
    'DYCKENHEINS': {'wat': 'Detailhandel of groothandel in mode of lifestyle producten.', 'groot': 'Klein bedrijf.', 'dmu': 'Eigenaar of manager.', 'kans': 'Geschat 1-2 printers | Kans: Laag - klein bedrijf met beperkte printbehoefte.'},
    'DWS Safe & Secure B.V.': {'wat': 'Beveiligingsbedrijf actief in fysieke en digitale beveiliging.', 'groot': 'Klein tot middelgroot bedrijf.', 'dmu': 'Directeur of operations manager.', 'kans': 'Geschat 2-4 printers | Kans: Midden - kantoor met rapportages en documentatie.'},
    'DVS Filtertechniek': {'wat': 'Technisch bedrijf gespecialiseerd in filtersystemen voor industrie.', 'groot': 'Klein gespecialiseerd bedrijf.', 'dmu': 'Directeur of technisch manager.', 'kans': 'Geschat 1-3 printers | Kans: Midden - technisch bedrijf met tekeningen en documentatie.'},
    'Dutchpacks B.V.': {'wat': 'Verpakkingsbedrijf dat verpakkingsoplossingen levert aan bedrijven.', 'groot': 'Middelgroot bedrijf.', 'dmu': 'Commercieel directeur of inkoper.', 'kans': 'Geschat 2-4 printers | Kans: Hoog - veel printwerk voor labels en administratie.'},
    'dUTCHCREEN B.V.': {'wat': 'Bedrijf actief in zeefdruk of screenprinting voor promotionele producten.', 'groot': 'Klein bedrijf.', 'dmu': 'Eigenaar of productiemanager.', 'kans': 'Geschat 1-2 printers | Kans: Midden - kantoorprinters naast productiemachines.'},
    'Dutch Petfood': {'wat': 'Producent of leverancier van dierenvoeding voor de Nederlandse markt.', 'groot': 'Middelgroot productiebedrijf.', 'dmu': 'Operations manager of directeur.', 'kans': 'Geschat 2-4 printers | Kans: Midden - kantoor en kwaliteitsdocumentatie.'},
    'Dutch Pet Import B.V.': {'wat': 'Importeur en distributeur van dierbenodigdheden en dierenvoeding.', 'groot': 'Klein tot middelgroot handelsbedrijf.', 'dmu': 'Directeur of logistiek manager.', 'kans': 'Geschat 2-3 printers | Kans: Midden - handelsbedrijf met administratie en magazijn.'},
    'Dutch Mushroom Projects BV': {'wat': 'Bedrijf gespecialiseerd in champignonteelt of paddenstoelgerelateerde projecten.', 'groot': 'Klein gespecialiseerd bedrijf.', 'dmu': 'Directeur of eigenaar.', 'kans': 'Geschat 1-2 printers | Kans: Laag - agrarisch bedrijf met beperkte kantooractiviteit.'},
    'Dutch Lighting Solutions': {'wat': 'Leverancier van verlichtingsoplossingen voor bedrijven en projecten.', 'groot': 'Klein tot middelgroot bedrijf.', 'dmu': 'Directeur of projectmanager.', 'kans': 'Geschat 2-3 printers | Kans: Midden - offertes en technische tekeningen.'},
    'Dutch Hills Harley-Davidson': {'wat': 'Officiele Harley-Davidson dealer met verkoop en service van motoren.', 'groot': 'Klein dealerbedrijf.', 'dmu': 'Eigenaar of vestigingsmanager.', 'kans': 'Geschat 2-4 printers | Kans: Hoog - balie, werkplaats en kantoor met printbehoefte.'},
    'Dutch Graphic Group': {'wat': 'Grafisch bedrijf actief in drukwerk, ontwerp of mediaproductie.', 'groot': 'Middelgroot bedrijf.', 'dmu': 'Directeur of productiemanager.', 'kans': 'Geschat 2-4 printers | Kans: Midden - kantoorprinters naast productiemachines.'},
    'Dutch Electro BV': {'wat': 'Elektrotechnisch installatiebedrijf of groothandel in elektromaterialen.', 'groot': 'Klein tot middelgroot bedrijf.', 'dmu': 'Directeur of werkvoorbereider.', 'kans': 'Geschat 2-4 printers | Kans: Hoog - veel documentatie en technische tekeningen.'},
    'Dutch detailing center': {'wat': 'Gespecialiseerd bedrijf in autopoets en detailing services.', 'groot': 'Klein bedrijf.', 'dmu': 'Eigenaar.', 'kans': 'Geschat 1 printer | Kans: Laag - kleine werkplaats met minimale kantooractiviteit.'},
    'Dutch Decor': {'wat': 'Bedrijf in interieurartikelen, decoratie of woonstyling.', 'groot': 'Klein tot middelgroot bedrijf.', 'dmu': 'Eigenaar of inkoopmanager.', 'kans': 'Geschat 1-2 printers | Kans: Midden - retailbedrijf met backoffice.'},
    'driessen stoffen': {'wat': 'Textielgroothandel of stoffenwinkel gespecialiseerd in stoffen en gordijnen.', 'groot': 'Klein familiebedrijf.', 'dmu': 'Eigenaar.', 'kans': 'Geschat 1 printer | Kans: Laag - kleine winkel met beperkte printbehoefte.'},
    'Driessen Food': {'wat': 'Voedingsmiddelenbedrijf actief in productie of distributie van voeding.', 'groot': 'Middelgroot bedrijf.', 'dmu': 'Directeur of operations manager.', 'kans': 'Geschat 2-4 printers | Kans: Hoog - kwaliteitsdocumentatie, labels en kantoor.'},
}

d['info'].update(nieuw)

with open(path, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print('Klaar - nu ' + str(len(d['info'])) + ' bedrijven in JSON')
