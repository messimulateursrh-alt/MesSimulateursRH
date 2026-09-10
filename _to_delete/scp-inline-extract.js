var LABELS_AGE_SCP = {
  'moins21': 'moins de 21 ans',
  '21-25': '21 à 25 ans',
  '26plus': '26 ans et plus'
};

function calculerSalaireContratPro(){
  var trancheAge = document.getElementById('trancheAgeSCP').value;
  var avecBacPro = document.getElementById('qualifSCP').checked;
  var resultBox = document.getElementById('resultSCP');

  var resultat = salaireMinimumContratPro(trancheAge, avecBacPro);
  if (!resultat){
    resultBox.classList.remove('show');
    return;
  }

  var salaireBrut = resultat.salaireBrut;

  document.getElementById('montantSCP').textContent = euros(salaireBrut) + ' / mois';
  document.getElementById('detailSCP').textContent = (resultat.pourcentage * 100).toFixed(0) + '% du SMIC brut mensuel, pour un salarié de ' + LABELS_AGE_SCP[trancheAge] + (trancheAge === '26plus' ? '' : (avecBacPro ? ', titulaire d\'un bac professionnel ou plus' : ', sans bac professionnel')) + '.';

  var noteMinConv = trancheAge === '26plus' ? ' Vérifiez le minimum conventionnel de branche : il peut être plus favorable (85% de ce minimum, à comparer au SMIC).' : '';
  document.getElementById('breakdownSCP').innerHTML =
    'SMIC brut mensuel de référence : ' + euros(BAREME_2026.SMIC_BRUT_MENSUEL) + '<br>' +
    'Pourcentage applicable : ' + (resultat.pourcentage * 100).toFixed(0) + '%<br>' +
    'Calcul : ' + euros(BAREME_2026.SMIC_BRUT_MENSUEL) + ' × ' + (resultat.pourcentage * 100).toFixed(0) + '% = <strong>' + euros(salaireBrut) + '</strong><br>' +
    'Référence : art. D6325-14 et D6325-15 du Code du travail. Minimum légal — vérifiez votre convention collective, qui peut être plus favorable.' + noteMinConv;

  var net = estimerNetContratPro(salaireBrut);
  document.getElementById('netEstimateSCP').innerHTML =
    'Net réel estimé : <strong>' + euros(net.net) + ' / mois</strong>. Contrairement à l\'apprentissage, le brut est intégralement soumis aux cotisations salariales et à la CSG/CRDS de droit commun (' + euros(net.cotisations.total) + '), sans seuil d\'exonération.';

  resultBox.classList.add('show');
}

function telechargerPDF_SCP(){
  var trancheAge = document.getElementById('trancheAgeSCP').value;
  var avecBacPro = document.getElementById('qualifSCP').checked;

  var resultat = salaireMinimumContratPro(trancheAge, avecBacPro);
  if (!resultat) return;

  var salaireBrut = resultat.salaireBrut;
  var net = estimerNetContratPro(salaireBrut);

  var lignes = [
    { label: 'Âge', value: LABELS_AGE_SCP[trancheAge] },
    { label: 'Niveau de qualification', value: trancheAge === '26plus' ? 'sans effet à partir de 26 ans' : (avecBacPro ? 'bac professionnel ou plus' : 'sans bac professionnel') },
    { label: 'SMIC brut mensuel de référence', value: euros(BAREME_2026.SMIC_BRUT_MENSUEL) },
    { label: 'Pourcentage applicable', value: (resultat.pourcentage * 100).toFixed(0) + '%' },
    { label: 'Salaire minimum brut mensuel', value: euros(salaireBrut) },
    { label: 'Cotisations salariales + CSG/CRDS estimées', value: euros(net.cotisations.total) },
    { label: 'Net réel estimé', value: euros(net.net), type: 'total' }
  ];

  genererPDFSimulation({
    titre: "Simulation de salaire minimum en contrat de professionnalisation",
    sousTitre: 'Minimum légal brut et net estimé',
    lignes: lignes,
    disclaimer: "Simulateur indicatif basé sur les articles D6325-14 et D6325-15 du Code du travail et le SMIC en vigueur au 1er juin 2026. Ne tient pas compte d'un minimum conventionnel de branche éventuellement plus favorable (notamment à partir de 26 ans, où 85% de ce minimum peut dépasser le SMIC) ni de la mutuelle d'entreprise si elle est obligatoire.",
    nomFichier: 'simulation-salaire-contrat-professionnalisation.pdf'
  });
}
