# models.py

from sqlalchemy import (
    Column, Integer, String, Date, Numeric, ForeignKey, 
    UniqueConstraint, Text, Boolean, CheckConstraint 
)
from sqlalchemy.orm import relationship, declarative_base

# Définition de la base déclarative pour SQLAlchemy
Base = declarative_base()

# ===================================================================
# --- TABLES DE RÉFÉRENCE: HIERARCHIE ADMINISTRATIVE ET ACADÉMIQUE ---
# ===================================================================

class Institution(Base):
    __tablename__ = 'institutions'
    __table_args__ = {'extend_existing': True}
    
    id_institution = Column(String(32), primary_key=True) 
    nom = Column(String(255), nullable=False, unique=True)
    type_institution = Column(String(10), nullable=False)
    description = Column(Text, nullable=True)
    
    composantes = relationship("Composante", back_populates="institution")


class Composante(Base):
    __tablename__ = 'composantes'
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(10), primary_key=True)
    label = Column(String(100))
    description = Column(Text, nullable=True) 
    
    id_institution = Column(String(32), ForeignKey('institutions.id_institution'), nullable=False) 
    institution = relationship("Institution", back_populates="composantes")
    
    mentions = relationship("Mention", backref="composante")

    # 🚨 CORRECTION DANS COMPOSANTE: Utiliser back_populates
    enseignants_permanents = relationship("Enseignant", back_populates="composante_attachement")


class Domaine(Base):
    __tablename__ = 'domaines'
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(10), primary_key=True)
    label = Column(String(100))
    description = Column(Text, nullable=True) 
    
    mentions = relationship("Mention", backref="domaine")


class Mention(Base):
    __tablename__ = 'mentions'
    __table_args__ = (
        UniqueConstraint('code_mention', 'composante_code', name='unique_mention_code_composante'),
        {'extend_existing': True}
    )
    
    id_mention = Column(String(50), primary_key=True) 
    code_mention = Column(String(20), nullable=False)
    label = Column(String(100))
    description = Column(Text, nullable=True) 
    
    composante_code = Column(String(10), ForeignKey('composantes.code'), nullable=False)
    domaine_code = Column(String(10), ForeignKey('domaines.code'), nullable=False)
    
    parcours = relationship("Parcours", backref="mention")


class Parcours(Base):
    __tablename__ = 'parcours'
    __table_args__ = (
        UniqueConstraint('code_parcours', 'mention_id', name='unique_parcours_code_mention'),
        {'extend_existing': True}
    )
    
    id_parcours = Column(String(50), primary_key=True)
    code_parcours = Column(String(20), nullable=False)
    label = Column(String(100))
    description = Column(Text, nullable=True) 
    
    mention_id = Column(String(50), ForeignKey('mentions.id_mention'), nullable=False)
    
    date_creation = Column(Integer, nullable=True)
    date_fin = Column(Integer, nullable=True)

# -------------------------------------------------------------------
# --- TABLES DE RÉFÉRENCE: STRUCTURE LMD (CYCLE, NIVEAU, SEMESTRE) ---
# -------------------------------------------------------------------

class Cycle(Base):
    __tablename__ = 'cycles'
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(10), primary_key=True)
    label = Column(String(50), unique=True, nullable=False)
    
    niveaux = relationship("Niveau", back_populates="cycle")
    suivi_credits = relationship("SuiviCreditCycle", back_populates="cycle") # Ajout relation

class Niveau(Base):
    __tablename__ = 'niveaux'
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(10), primary_key=True)
    label = Column(String(50)) 
    
    cycle_code = Column(String(10), ForeignKey('cycles.code'), nullable=False)
    cycle = relationship("Cycle", back_populates="niveaux")
    
    semestres = relationship("Semestre", back_populates="niveau")
    
class Semestre(Base):
    __tablename__ = 'semestres'
    __table_args__ = (
        # Réintroduction de la contrainte pour assurer la cohérence des codes L1_S01
        UniqueConstraint('niveau_code', 'numero_semestre', name='uq_niveau_numero_semestre'), 
        {'extend_existing': True}
    )
    
    code_semestre = Column(String(10), primary_key=True) # Ex: L1_S01
    numero_semestre = Column(String(10), nullable=False) # Ex: S01
    
    niveau_code = Column(String(10), ForeignKey('niveaux.code'), nullable=False)
    niveau = relationship("Niveau", back_populates="semestres")
    
    inscriptions = relationship("Inscription", back_populates="semestre")
    unites_enseignement = relationship("UniteEnseignement", back_populates="semestre") # Correction back_populates

# -------------------------------------------------------------------
# --- TABLES DE RÉFÉRENCE: UNITÉS D'ENSEIGNEMENT ET SESSIONS ---
# -------------------------------------------------------------------

class UniteEnseignement(Base):
    __tablename__ = 'unites_enseignement'
    __table_args__ = {'extend_existing': True}
    
    id_ue = Column(String(50), primary_key=True)
    code_ue = Column(String(20), unique=True, nullable=False)
    intitule = Column(String(255), nullable=False)
    credit_ue = Column(Integer, nullable=False)
    
    code_semestre = Column(String(10), ForeignKey('semestres.code_semestre'), nullable=False)
    semestre = relationship("Semestre", back_populates="unites_enseignement") 
    
    elements_constitutifs = relationship("ElementConstitutif", back_populates="unite_enseignement")
    resultats = relationship("ResultatUE", back_populates="unite_enseignement")


class ElementConstitutif(Base):
    __tablename__ = 'elements_constitutifs'
    __table_args__ = {'extend_existing': True}
    
    id_ec = Column(String(50), primary_key=True)
    code_ec = Column(String(20), unique=True, nullable=False)
    intitule = Column(String(255), nullable=False)
    coefficient = Column(Integer, default=1, nullable=False)
    
    id_ue = Column(String(50), ForeignKey('unites_enseignement.id_ue'), nullable=False)
    
    unite_enseignement = relationship("UniteEnseignement", back_populates="elements_constitutifs")
    
    notes = relationship("Note", back_populates="element_constitutif")

    # 🚨 CORRECTION DANS ElementConstitutif: Utiliser back_populates
    volumes_horaires = relationship("VolumeHoraireEC", back_populates="element_constitutif")
    affectations = relationship("AffectationEC", back_populates="element_constitutif") # Reste backref ici (vérifiez si cela cause un conflit avec AffectationEC)

# ===================================================================
# --- TABLES DE RÉFÉRENCE: UNITÉS D'ENSEIGNEMENT ET SESSIONS ---
# ===================================================================
class SessionExamen(Base):
    """ Table conservée pour les sessions d'examen (ex: Normale, Rattrapage) """
    __tablename__ = 'sessions_examen'
    __table_args__ = {'extend_existing': True}
    
    code_session = Column(String(5), primary_key=True) # Ex: N, R
    label = Column(String(50), nullable=False, unique=True) # Ex: Normale, Rattrapage
    
    # Collection de toutes les Notes obtenues pour cette session
    notes_session = relationship("Note", back_populates="session")
    
    # 🚨 CORRECTION FINALE : Collection de tous les ResultatUE obtenus pour cette session
    resultats_ue_session = relationship("ResultatUE", back_populates="session")


# -------------------------------------------------------------------
# --- TABLES DE RÉFÉRENCE: TYPE D'INSCRIPTION ---
# -------------------------------------------------------------------

class ModeInscription(Base): # 👈 CHANGEMENT DE NOM DE CLASSE
    __tablename__ = 'modes_inscription' # 👈 CHANGEMENT DE NOM DE TABLE
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(10), primary_key=True) # Ex: 'CLAS', 'HYB'
    label = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True) 
    
    # Mise à jour de la relation
    inscriptions = relationship("Inscription", back_populates="mode_inscription") # 👈 CHANGEMENT DE NOM DE RELATION

# ===================================================================
# --- TABLES DE RÉFÉRENCE: TYPE DE FORMATION ---
# ===================================================================

class TypeFormation(Base):
    __tablename__ = 'types_formation'
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(10), primary_key=True) # Ex: FI, FC, FOAD
    label = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # 🚨 Nouvelle relation : Pour lier aux inscriptions
    inscriptions = relationship("Inscription", back_populates="type_formation")
    

# ===================================================================
# --- TABLES DE DONNÉES: ÉTUDIANT, INSCRIPTION, RÉSULTATS ---
# ===================================================================

class AnneeUniversitaire(Base):
    __tablename__ = 'annees_universitaires'
    __table_args__ = {'extend_existing': True} 
    
    annee = Column(String(9), primary_key=True)
    description = Column(Text, nullable=True) 
    ordre_annee = Column(Integer, unique=True, nullable=False) # 👈 AJOUT IMPORTANT
    
    # Correction des back_populates
    inscriptions = relationship("Inscription", back_populates="annee_univ")
    notes_obtenues = relationship("Note", back_populates="annee_univ")
    resultats_ue = relationship("ResultatUE", back_populates="annee_univ") # 👈 AJOUT
    volumes_horaires_ec = relationship("VolumeHoraireEC", back_populates="annee_univ") # 👈 AJOUT
    affectations_ec = relationship("AffectationEC", back_populates="annee_univ_affectation")


class Etudiant(Base):
    __tablename__ = 'etudiants'
    __table_args__ = (
        # ❌ CETTE LIGNE EST SUPPRIMÉE : 
        # CheckConstraint("sexe IN ('M', 'F', 'Autre')", name='check_sexe_mf_autre'),
        
        # ⚠️ NOTE: Si vous aviez d'autres arguments dans __table_args__ (comme UniqueConstraint, etc.), 
        # ils doivent être conservés. Si seule la contrainte de sexe était présente, 
        # vous pouvez utiliser un tuple vide ou supprimer complètement __table_args__.
        {'extend_existing': True} 
    )
    
    code_etudiant = Column(String(50), primary_key=True) 

    # 🚨 CORRECTION: Contrainte UNIQUE retirée
    numero_inscription = Column(String(50))
    
    nom = Column(String(100), nullable=False)
    prenoms = Column(String(150))
    sexe = Column(String(20)) # Laissez le type String(20)

    naissance_date = Column(Date, nullable=True)
    naissance_lieu = Column(String(100))
    nationalite = Column(String(50))
    
    bacc_annee = Column(Integer, nullable=True)
    bacc_serie = Column(String(50)) 
    bacc_centre = Column(String(100))
    
    adresse = Column(String(255))
    telephone = Column(String(50))
    mail = Column(String(100))
    
    cin = Column(String(100))
    cin_date = Column(Date, nullable=True)
    cin_lieu = Column(String(100))

    # Relations 
    inscriptions = relationship("Inscription", back_populates="etudiant")
    # 🚨 MISE À JOUR: Utilisation de 'notes_obtenues' pour harmoniser avec la classe Note
    notes_obtenues = relationship("Note", back_populates="etudiant") 
    credits_cycles = relationship("SuiviCreditCycle", back_populates="etudiant")
    
    # 🚨 AJOUT DE LA RELATION
    resultats_ue = relationship("ResultatUE", back_populates="etudiant") 
    resultats_semestre = relationship("ResultatSemestre", back_populates="etudiant_resultat") # Gardé backref ici pour simplicité


class Inscription(Base):
    __tablename__ = 'inscriptions'
    __table_args__ = (
        UniqueConstraint(
            'code_etudiant', 
            'annee_universitaire', 
            'id_parcours', 
            'code_semestre', 
            name='uq_etudiant_annee_parcours_semestre' 
        ),
        {'extend_existing': True} 
    )
    
    code_inscription = Column(String(50), primary_key=True)
    
    # Clés étrangères
    code_etudiant = Column(String(50), ForeignKey('etudiants.code_etudiant'), nullable=False)
    annee_universitaire = Column(String(9), ForeignKey('annees_universitaires.annee'), nullable=False)
    id_parcours = Column(String(50), ForeignKey('parcours.id_parcours'), nullable=False)
    code_semestre = Column(String(10), ForeignKey('semestres.code_semestre'), nullable=False)
    # Mise à jour de la clé étrangère
    code_mode_inscription = Column(String(10), ForeignKey('modes_inscription.code'), nullable=False) # 👈 CHANGEMENT DE TABLE RÉFÉRENCÉE et NOM DE COLONNE
    # 🚨 NOUVELLE CLÉ ÉTRANGÈRE : code_type_formation
    code_type_formation = Column(String(10), ForeignKey('types_formation.code'), nullable=False, default='FI')
    
    # CREDIT et VALIDATION du SEMESTRE
    credit_acquis_semestre = Column(Integer, default=0) 
    is_semestre_valide = Column(Boolean, default=False) 
    
    # Relations
    etudiant = relationship("Etudiant", back_populates="inscriptions")
    annee_univ = relationship("AnneeUniversitaire", back_populates="inscriptions") 
    parcours = relationship("Parcours", backref="inscriptions")
    semestre = relationship("Semestre", back_populates="inscriptions")
    # Mise à jour de la relation
    mode_inscription = relationship("ModeInscription", back_populates="inscriptions") 
    type_formation = relationship("TypeFormation", back_populates="inscriptions")# 👈 CHANGEMENT DE NOM DE CLASSE ET DE RELATION


class ResultatSemestre(Base):
    """
    Table stockant le statut final de validation d'un semestre pour un étudiant, 
    incluant la moyenne et les crédits acquis (pour l'analyse de compensation).
    """
    __tablename__ = 'resultats_semestre'
    __table_args__ = (
        # 🚨 MISE À JOUR DE LA CONTRAINTE D'UNICITÉ : Ajout de 'code_session' 🚨
        UniqueConstraint('code_etudiant', 'code_semestre', 'annee_universitaire', 'code_session', name='uq_resultat_semestre_session'),
    )
    
    id_resultat = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés Étrangères
    code_etudiant = Column(String(50), ForeignKey('etudiants.code_etudiant'), nullable=False)
    code_semestre = Column(String(50), ForeignKey('semestres.code_semestre'), nullable=False)
    annee_universitaire = Column(String(10), ForeignKey('annees_universitaires.annee'), nullable=False)
    
    # 🚨 AJOUT DE LA CLÉ ÉTRANGÈRE VERS LA SESSION D'EXAMEN 🚨
    code_session = Column(String(5), ForeignKey('sessions_examen.code_session'), nullable=False)
    
    # Indicateur de validation (V, NV, AJ)
    statut_validation = Column(String(5), 
                               CheckConstraint("statut_validation IN ('V', 'NV', 'AJ')", name='check_statut_validation'), 
                               nullable=False)
    
    # Informations de performance
    credits_acquis = Column(Numeric(4, 1)) # Ex: 25.5 crédits sur 30
    moyenne_obtenue = Column(Numeric(4, 2)) # Ex: 9.85/20
    
    # Relations
    etudiant_resultat = relationship("Etudiant", back_populates="resultats_semestre")
    semestre = relationship("Semestre")
    session = relationship("SessionExamen", backref="resultats_semestre") 
    annee_univ = relationship("AnneeUniversitaire") # Utilise le backref dans AnneeUniversitaire si défini

    def __repr__(self):
        return (f"<ResultatSemestre {self.code_etudiant} - {self.code_semestre} "
                f"(Sess: {self.code_session}, Moy: {self.moyenne_obtenue}): {self.statut_validation}>")   
    
class ResultatUE(Base):
    """
    Table stockant la moyenne et le statut de validation d'une UE
    pour un étudiant, en utilisant les meilleures notes des EC entre sessions.
    """
    __tablename__ = 'resultats_ue'
    __table_args__ = (
        # Un seul résultat final par UE, étudiant, année et session
        UniqueConstraint('code_etudiant', 'id_ue', 'annee_universitaire', 'code_session', name='uq_resultat_ue_unique'),
    )
    
    id_resultat_ue = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés Étrangères
    code_etudiant = Column(String(50), ForeignKey('etudiants.code_etudiant'), nullable=False)
    id_ue = Column(String(50), ForeignKey('unites_enseignement.id_ue'), nullable=False)
    annee_universitaire = Column(String(9), ForeignKey('annees_universitaires.annee'), nullable=False)
    code_session = Column(String(5), ForeignKey('sessions_examen.code_session'), nullable=False) 
    
    # RÉSULTAT CALCULÉ
    moyenne_ue = Column(Numeric(4, 2), nullable=False) # Moyenne calculée des EC capitalisés (ex: 10.00)
    is_ue_acquise = Column(Boolean, default=False, nullable=False) # TRUE si moyenne_ue >= 10
    credit_obtenu = Column(Integer, default=0, nullable=False) # Crédit total de l'UE (0 ou credit_ue)

    # Relations
    etudiant = relationship("Etudiant", back_populates="resultats_ue") 
    unite_enseignement = relationship("UniteEnseignement", back_populates="resultats")
    
    # 🚨 VÉRIFICATION OK : Ce back_populates pointe vers le nouvel attribut dans SessionExamen
    session = relationship("SessionExamen", back_populates="resultats_ue_session") 
    
    annee_univ = relationship("AnneeUniversitaire", back_populates="resultats_ue")
    
    def __repr__(self):
        return (f"<ResultatUE {self.code_etudiant} - {self.id_ue} "
                f"(Sess: {self.code_session}, Moy: {self.moyenne_ue}): {self.is_ue_acquise}>")

class Note(Base):
    __tablename__ = 'notes'
    __table_args__ = (
        UniqueConstraint(
            'code_etudiant', 
            'id_ec', 
            'annee_universitaire',
            'code_session',
            name='uq_etudiant_ec_annee_session' 
        ),
        {'extend_existing': True}
    )
    
    id_note = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés Étrangères Composites
    code_etudiant = Column(String(50), ForeignKey('etudiants.code_etudiant'), nullable=False)
    id_ec = Column(String(50), ForeignKey('elements_constitutifs.id_ec'), nullable=False)
    annee_universitaire = Column(String(9), ForeignKey('annees_universitaires.annee'), nullable=False)
    code_session = Column(String(5), ForeignKey('sessions_examen.code_session'), nullable=False)
    
    # Donnée Principale
    valeur_note = Column(Numeric(5, 2), nullable=False) # Note obtenue (permet les décimales)

    # Relations
    # 🚨 MISE À JOUR : Changement de backref pour correspondre au nom dans Etudiant
    etudiant = relationship("Etudiant", back_populates="notes_obtenues") 
    element_constitutif = relationship("ElementConstitutif", back_populates="notes")
    # 🚨 MISE À JOUR : Changement de backref à back_populates
    annee_univ = relationship("AnneeUniversitaire", back_populates="notes_obtenues")
    # 🚨 MISE À JOUR : Changement de backref à back_populates
    session = relationship("SessionExamen", back_populates="notes_session")

    def __repr__(self):
        return (f"<Note {self.code_etudiant} - {self.id_ec} "
                f"({self.annee_universitaire}, {self.code_session}): {self.valeur_note}>")


class SuiviCreditCycle(Base):
    __tablename__ = 'suivi_credits_cycles'
    __table_args__ = (
        UniqueConstraint('code_etudiant', 'cycle_code', name='uq_etudiant_cycle_credit'),
        {'extend_existing': True}
    )
    
    id_suivi = Column(Integer, primary_key=True, autoincrement=True)
    
    code_etudiant = Column(String(50), ForeignKey('etudiants.code_etudiant'), nullable=False)
    cycle_code = Column(String(10), ForeignKey('cycles.code'), nullable=False)
    
    credit_total_acquis = Column(Integer, default=0, nullable=False)
    is_cycle_valide = Column(Boolean, default=False) 
    
    # 🚨 CORRECTION: back_populates déjà corrigé sur la classe Etudiant
    etudiant = relationship("Etudiant", back_populates="credits_cycles") 
    cycle = relationship("Cycle", back_populates="suivi_credits")

    # ===================================================================
# --- TABLES DE DONNÉES: ENSEIGNANT ET CHARGE D'ENSEIGNEMENT ---
# ===================================================================

class Enseignant(Base):
    __tablename__ = 'enseignants'
    __table_args__ = (
        # Assure l'unicité de CIN si non nul
        UniqueConstraint('cin', name='uq_enseignant_cin', deferrable=True),
        {'extend_existing': True}
    )
    
    id_enseignant = Column(String(50), primary_key=True) 
    matricule = Column(String(50), unique=True, nullable=True) # Matricule si permanent

    nom = Column(String(100), nullable=False)
    prenoms = Column(String(150))
    sexe = Column(String(20)) 
    date_naissance = Column(Date, nullable=True)
    
    # Renseignement administratifs/carrière
    grade = Column(String(50))
    # 🚨 CORRECTION CRUCIALE : Tout sur une seule ligne si possible ou structure stricte
    statut = Column(String(10), 
                    CheckConstraint("statut IN ('PERM', 'VAC')", name='check_statut_enseignant'), # Argument positionnel (la contrainte)
                    nullable=False) # Argument mot-clé, doit venir APRÈS la contrainte si elle n'est pas nommée

    # Affectation composante (Obligatoire pour un permanent)
    code_composante_affectation = Column(String(10), 
                                         ForeignKey('composantes.code'), 
                                         nullable=True)
    
    # Coordonnées / Identité
    cin = Column(String(100))
    cin_date = Column(Date, nullable=True)
    cin_lieu = Column(String(100))
    telephone = Column(String(50))
    mail = Column(String(100))
    rib = Column(String(100)) # Relevé d'Identité Bancaire

    # 🚨 CORRECTION DANS ENSEIGNANT: Renommer la relation côté enfant
    composante_attachement = relationship("Composante", back_populates="enseignants_permanents")
    charges_enseignement = relationship("AffectationEC", back_populates="enseignant")

    # 🚨 NOUVELLE RELATION : Présidences de jury
    presidences_jury = relationship("Jury", back_populates="enseignant_president") # 👈 NOUVEL AJOUT


class TypeEnseignement(Base):
    """ Types de charge: Cours, TD, TP """
    __tablename__ = 'types_enseignement'
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(10), primary_key=True) # Ex: C, TD, TP
    label = Column(String(50), unique=True, nullable=False)
    
    volumes_horaires = relationship("VolumeHoraireEC", back_populates="type_enseignement")
    affectations = relationship("AffectationEC", back_populates="type_enseignement")


class VolumeHoraireEC(Base):
    """
    Volume horaire théorique pour un EC, réparti par type et PAR ANNÉE.
    Ceci permet la gestion d'historique.
    """
    __tablename__ = 'volume_horaire_ec'
    __table_args__ = (
        # Clé composée pour l'historique
        UniqueConstraint('id_ec', 'code_type_enseignement', 'annee_universitaire', name='uq_ec_vh_type_annee'),
        {'extend_existing': True}
    )
    
    id_volume_horaire = Column(Integer, primary_key=True, autoincrement=True)
    
    id_ec = Column(String(50), ForeignKey('elements_constitutifs.id_ec'), nullable=False)
    code_type_enseignement = Column(String(10), ForeignKey('types_enseignement.code'), nullable=False)
    # 🚨 AJOUT POUR L'HISTORIQUE 🚨
    annee_universitaire = Column(String(9), ForeignKey('annees_universitaires.annee'), nullable=False)
    
    volume_heure = Column(Numeric(5, 2), nullable=False) 

    # Relations
    element_constitutif = relationship("ElementConstitutif", back_populates="volumes_horaires")
    type_enseignement = relationship("TypeEnseignement", back_populates="volumes_horaires")
    # 🚨 MISE À JOUR : Changement de backref à back_populates
    annee_univ = relationship("AnneeUniversitaire", back_populates="volumes_horaires_ec")


class AffectationEC(Base):
    """
    Associe un enseignant à un EC pour un type d'enseignement et une année universitaire donnés.
    C'est la table qui gère la charge réelle.
    """
    __tablename__ = 'affectations_ec'
    __table_args__ = (
        # Un EC, pour un type d'enseignement et une année donnée, 
        # ne doit être assuré que par un seul enseignant (pour simplifier la gestion de la responsabilité)
        UniqueConstraint('id_ec', 'code_type_enseignement', 'annee_universitaire', name='uq_affectation_unique'), 
        {'extend_existing': True}
    )
    
    id_affectation = Column(Integer, primary_key=True, autoincrement=True)
    
    id_enseignant = Column(String(50), ForeignKey('enseignants.id_enseignant'), nullable=False)
    id_ec = Column(String(50), ForeignKey('elements_constitutifs.id_ec'), nullable=False)
    code_type_enseignement = Column(String(10), ForeignKey('types_enseignement.code'), nullable=False)
    annee_universitaire = Column(String(9), ForeignKey('annees_universitaires.annee'), nullable=False)
    
    # Le volume horaire peut être repris du VolumeHoraireEC ou spécifié ici si ajustement (optionnel)
    volume_heure_effectif = Column(Numeric(5, 2), nullable=True) 

    # Relations
    enseignant = relationship("Enseignant", back_populates="charges_enseignement")
    element_constitutif = relationship("ElementConstitutif", back_populates="affectations")
    type_enseignement = relationship("TypeEnseignement", back_populates="affectations")
    annee_univ_affectation = relationship("AnneeUniversitaire", back_populates="affectations_ec")

# ===================================================================
# --- TABLES DE DONNÉES: GESTION DES JURYS D'EXAMEN (MODIFIÉE) ---
# ===================================================================

class Jury(Base):
    """
    Associe un enseignant (président) à un jury de session de semestre.
    La nomination vaut pour toutes les sessions (N et R) du semestre concerné.
    """
    __tablename__ = 'jurys'
    __table_args__ = (
        # CHANGEMENT : Un seul président pour un semestre et une année,
        # la nomination s'appliquant implicitement aux sessions N et R.
        UniqueConstraint('code_semestre', 'annee_universitaire', name='uq_jury_unique'), 
        {'extend_existing': True}
    )
    
    id_jury = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clés Étrangères Composites
    id_enseignant = Column(String(50), ForeignKey('enseignants.id_enseignant'), nullable=False)
    code_semestre = Column(String(10), ForeignKey('semestres.code_semestre'), nullable=False)
    annee_universitaire = Column(String(9), ForeignKey('annees_universitaires.annee'), nullable=False)
    
    # ❌ SUPPRESSION : La colonne code_session n'est plus nécessaire.
    # code_session = Column(String(5), ForeignKey('sessions_examen.code_session'), nullable=False)
    
    date_nomination = Column(Date, nullable=True) 
    
    # Relations
    enseignant_president = relationship("Enseignant", back_populates="presidences_jury")
    semestre_jury = relationship("Semestre")
    annee_univ_jury = relationship("AnneeUniversitaire")
    
    # ❌ SUPPRESSION de la relation vers SessionExamen
    # session_jury = relationship("SessionExamen") 
    
    def __repr__(self):
        return (f"<Jury Sémestre {self.code_semestre} ({self.annee_universitaire}) "
                f"présidé par {self.id_enseignant}>")