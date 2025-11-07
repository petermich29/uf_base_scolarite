# import_data.py

import pandas as pd
import sys
import logging
from tqdm import tqdm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DataError
from datetime import date 

import config
import database_setup
from models import (
    Institution, Composante, Domaine, Mention, Parcours, 
    AnneeUniversitaire, Etudiant, Inscription,
    # CLASSES LMD & TYPE INSCRIPTION
    Cycle, Niveau, Semestre, TypeInscription, SessionExamen
)

# Configuration du logging (inchangée)
logging.basicConfig(filename='import_errors.log', 
                    filemode='w', 
                    encoding='utf-8',
                    level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def safe_string(s):
    """Assure le nettoyage des chaînes de caractères."""
    if s is None or not isinstance(s, str):
        return s
    
    s = str(s).strip()
    return s


# ----------------------------------------------------------------------
# FONCTIONS D'IMPORTATION DES DONNÉES DE RÉFÉRENCE FIXES
# ----------------------------------------------------------------------

def import_fixed_references(session: Session):
    """
    Insère les données de référence fixes (Cycles, Niveaux, Semestres, Types Inscription, Sessions).
    """
    print("\n--- 1. Importation des Données de Référence Fixes (LMD & Types) ---")
    
    # 1. Cycles
    cycles_data = [
        {'code': 'L', 'label': 'Licence'},
        {'code': 'M', 'label': 'Master'},
        {'code': 'D', 'label': 'Doctorat'},
    ]
    for data in cycles_data:
        session.merge(Cycle(**data))
    
    # 2. Niveaux et Semestres 
    niveau_semestre_map = {
        'L1': ('L', ['S01', 'S02']),
        'L2': ('L', ['S03', 'S04']),
        'L3': ('L', ['S05', 'S06']),
        'M1': ('M', ['S07', 'S08']),
        'M2': ('M', ['S09', 'S10']),
        'D1': ('D', ['S11', 'S12']),
        'D2': ('D', ['S13', 'S14']),
        'D3': ('D', ['S15', 'S16']),
    }
    
    all_semestre_codes = [] 
    
    for niv_code, (cycle_code, sem_list) in niveau_semestre_map.items():
        session.merge(Niveau(code=niv_code, label=niv_code, cycle_code=cycle_code))
        
        for sem_num in sem_list:
            
            # Insertion de la clé complète (NIVEAU_SEMESTRE) - Ex: L1_S01
            sem_code_complet = f"{niv_code}_{sem_num}" 
            session.merge(Semestre(
                code_semestre=sem_code_complet,
                numero_semestre=sem_num,
                niveau_code=niv_code 
            ))
            all_semestre_codes.append(sem_code_complet) 

    # 3. Types Inscription
    types_inscription_data = [
        {'code': 'CLAS', 'label': 'Classique'},
        {'code': 'HYB', 'label': 'Hybride'},
    ]
    for data in types_inscription_data:
        session.merge(TypeInscription(**data))
        
    # 4. Insertion des Sessions d'Examen (SessionExamen) 🚨
    session_examen_data = [
        {'code_session': 'N', 'label': 'Normale'},
        {'code_session': 'R', 'label': 'Rattrapage'},
    ]
                          
    for sess in session_examen_data:
        session.merge(SessionExamen(**sess))
        
    session.commit()
    print("✅ Données de Référence LMD, Types Inscription et Sessions d'Examen insérées.")


# ----------------------------------------------------------------------
# FONCTIONS D'IMPORTATION UNITAIRE DE LA STRUCTURE ACADÉMIQUE
# ----------------------------------------------------------------------

def _import_institutions(session: Session) -> bool:
    """Charge et importe la table Institution."""
    print("\n--- Importation des Institutions ---")
    try:
        df_inst = pd.read_excel(config.INSTITUTION_FILE_PATH)
        df_inst.columns = df_inst.columns.str.lower().str.replace(' ', '_')
        df_inst = df_inst.where(pd.notnull(df_inst), None)
        
        df_inst['institution_id'] = df_inst['institution_id'].astype(str).apply(safe_string)
        df_inst_clean = df_inst.drop_duplicates(subset=['institution_id']).dropna(subset=['institution_id'])
        
        for _, row in tqdm(df_inst_clean.iterrows(), total=len(df_inst_clean), desc="Institutions"):
            session.merge(Institution(
                id_institution=row['institution_id'], 
                nom=safe_string(row['institution_nom']),
                type_institution=safe_string(row['institution_type'])
                # description est optionnel
            ))
        
        session.commit()
        print("✅ Importation des Institutions terminée.")
        return True
        
    except Exception as e:
        print(f"❌ ERREUR: Impossible de lire ou d'importer le fichier Institutions. {e}", file=sys.stderr)
        session.rollback()
        return False


def _import_composantes(session: Session, df: pd.DataFrame):
    """Importe les Composantes (dépend d'Institution)."""
    print("\n--- Importation des Composantes ---")
    if 'composante' not in df.columns:
         print("Colonne 'composante' manquante dans les métadonnées.")
         return
         
    df_composantes = df[['composante', 'label_composante', 'institution_id']].drop_duplicates(subset=['composante']).dropna(subset=['composante', 'institution_id'])
    
    for _, row in tqdm(df_composantes.iterrows(), total=len(df_composantes), desc="Composantes"):
        session.merge(Composante(
            code=row['composante'], 
            label=safe_string(row['label_composante']),
            id_institution=row['institution_id'] 
            # description est optionnel
        ))


def _import_domaines(session: Session, df: pd.DataFrame):
    """Importe les Domaines."""
    print("\n--- Importation des Domaines ---")
    if 'domaine' not in df.columns:
         print("Colonne 'domaine' manquante dans les métadonnées.")
         return
         
    df_domaines = df[['domaine', 'label_domaine']].drop_duplicates(subset=['domaine']).dropna(subset=['domaine'])
    
    for _, row in tqdm(df_domaines.iterrows(), total=len(df_domaines), desc="Domaines"):
        session.merge(Domaine(code=row['domaine'], label=safe_string(row['label_domaine'])))


def _import_mentions(session: Session, df: pd.DataFrame):
    """Importe les Mentions (dépend de Composante et Domaine)."""
    print("\n--- Importation des Mentions ---")
    if 'id_mention' not in df.columns:
         print("Colonne 'id_mention' manquante dans les métadonnées.")
         return
         
    df_mentions_source = df[['mention', 'label_mention', 'id_mention', 'composante', 'domaine']].drop_duplicates(subset=['id_mention']).dropna(subset=['id_mention', 'composante', 'domaine', 'mention'])
    
    for _, row in tqdm(df_mentions_source.iterrows(), total=len(df_mentions_source), desc="Mentions"):
        session.merge(Mention(
            id_mention=row['id_mention'], 
            code_mention=safe_string(row['mention']),
            label=safe_string(row['label_mention']),
            composante_code=row['composante'], 
            domaine_code=row['domaine']
            # description est optionnel
        ))
    return df_mentions_source 


def _import_parcours(session: Session, df: pd.DataFrame, df_mentions_source: pd.DataFrame):
    """Importe les Parcours (dépend de Mention)."""
    print("\n--- Importation des Parcours ---")
    
    if 'id_parcours' not in df.columns:
         print("Colonne 'id_parcours' manquante dans les métadonnées.")
         return
         
    df_parcours = df[['id_parcours', 'parcours', 'label_parcours', 'id_mention', 'date_creation', 'date_fin']].copy()
    
    df_parcours = df_parcours.drop_duplicates(subset=['id_parcours'], keep='first').dropna(subset=['id_parcours', 'id_mention', 'parcours'])

    nombre_parcours_uniques = len(df_parcours)
    
    for _, row in tqdm(df_parcours.iterrows(), total=nombre_parcours_uniques, desc="Parcours"):
        
        # Le type Integer pour date_creation/fin est conservé
        date_creation_val = int(row['date_creation']) if pd.notna(row['date_creation']) and row['date_creation'] is not None else None
        date_fin_val = int(row['date_fin']) if pd.notna(row['date_fin']) and row['date_fin'] is not None else None
        
        session.merge(Parcours(
            id_parcours=row['id_parcours'], 
            code_parcours=safe_string(row['parcours']), 
            label=safe_string(row['label_parcours']),
            mention_id=row['id_mention'], 
            date_creation=date_creation_val,
            date_fin=date_fin_val
            # description est optionnel
        ))
    

def _load_and_clean_metadata():
    """Charge et nettoie le fichier de métadonnées académiques."""
    try:
        df = pd.read_excel(config.METADATA_FILE_PATH)
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        df = df.where(pd.notnull(df), None)
        print(f"Fichier de métadonnées académiques chargé. {len(df)} lignes trouvées.")
        
        # Nettoyage des clés
        df['institution_id'] = df['institution_id'].astype(str).apply(safe_string) 
        df['composante'] = df['composante'].astype(str).apply(safe_string)
        df['domaine'] = df['domaine'].astype(str).apply(safe_string)
        df['id_mention'] = df['id_mention'].astype(str).apply(safe_string) 
        df['id_parcours'] = df['id_parcours'].astype(str).apply(safe_string)
        
        return df
        
    except Exception as e:
        print(f"❌ ERREUR: Impossible de lire le fichier de métadonnées académiques. {e}", file=sys.stderr)
        return None
        
# ----------------------------------------------------------------------
# FONCTION ORCHESTRATRICE DE LA STRUCTURE ACADÉMIQUE
# ----------------------------------------------------------------------

def import_metadata_to_db():
    """
    Orchestre l'importation de la structure académique.
    """
    print(f"\n--- 2. Démarrage de l'importation des métadonnées ---")
    session = database_setup.get_session()

    try:
        if not _import_institutions(session):
            return

        df_metadata = _load_and_clean_metadata()
        if df_metadata is None:
            return

        _import_composantes(session, df_metadata) 
        _import_domaines(session, df_metadata)
        
        df_mentions_source = _import_mentions(session, df_metadata) 

        _import_parcours(session, df_metadata, df_mentions_source) 

        session.commit()
        print("\n✅ Importation des métadonnées académiques (Composante, etc.) terminée avec succès.")

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR D'IMPORTATION (Métadonnées): {e}", file=sys.stderr)
    finally:
        session.close()


# ----------------------------------------------------------------------
# FONCTIONS D'IMPORTATION UNITAIRE DES INSCRIPTIONS
# ----------------------------------------------------------------------

def _load_and_clean_inscriptions():
    """
    Charge, nettoie et enrichit le fichier d'inscriptions.
    MODIFIÉ: Utilise la colonne 'niveau' (L1, M1, etc.) pour enrichir le code_semestre.
    """
    try:
        df = pd.read_excel(config.INSCRIPTION_FILE_PATH)
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        date_cols = ['naissance_date', 'cin_date']
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True).dt.date
            
        df = df.where(pd.notnull(df), None) 
        print(f"Fichier XLSX d'inscriptions chargé. {len(df)} lignes trouvées.")
        
        # --- Nettoyage et Enrichissement des clés critiques ---
        if 'id_parcours_caractere' in df.columns:
            df.rename(columns={'id_parcours_caractere': 'id_parcours'}, inplace=True) 
        if 'id_parcours' in df.columns:
             df['id_parcours'] = df['id_parcours'].astype(str).apply(safe_string) 

        # Renommage des colonnes Semestre potentielles en 'code_semestre'
        if 'semestre_id' in df.columns:
            df.rename(columns={'semestre_id': 'code_semestre'}, inplace=True) 
        elif 'semestre' in df.columns and 'code_semestre' not in df.columns:
            df.rename(columns={'semestre': 'code_semestre'}, inplace=True)

        
        # 🚨 CORRECTION CRITIQUE 1: DÉTECTION ET UTILISATION DE LA COLONNE 'NIVEAU' 🚨
        if 'niveau' in df.columns:
            # 1. Renommer 'niveau' en 'niveau_code' pour l'utiliser dans la logique
            df.rename(columns={'niveau': 'niveau_code'}, inplace=True)
            print("✅ Colonne 'niveau' détectée et renommée en 'niveau_code'.")
        
        # 1. Nettoyage/Enrichissement du code_semestre (Doit être L1_S01)
        if 'code_semestre' in df.columns:
            df['code_semestre'] = df['code_semestre'].astype(str).apply(safe_string)
            
            # Application de l'enrichissement si la colonne niveau_code est maintenant présente
            if 'niveau_code' in df.columns:
                df['niveau_code'] = df['niveau_code'].astype(str).apply(safe_string)
                df['code_semestre'] = df.apply(
                    lambda row: f"{row['niveau_code']}_{row['code_semestre']}" 
                    # Enrichir seulement si le code n'est pas déjà au format L1_S01 (pas de '_')
                    if pd.notna(row.get('niveau_code')) 
                    and row['code_semestre']
                    and '_' not in str(row['code_semestre'])
                    else row['code_semestre'], 
                    axis=1
                )
                print("✅ Code_semestre enrichi avec le niveau (Ex: L1_S01).")
            else:
                 # Le message d'avertissement est conservé mais la cause est que ni 'niveau' ni 'niveau_code' n'a été trouvé
                 print("\n⚠️ ATTENTION: Colonne 'niveau' (ou 'niveau_code') manquante pour enrichir le code_semestre. Risque d'erreurs FK.")

        
        # 2. Renommage et Standardisation du Type Inscription
        if 'type_formation' in df.columns:
            
            # Renommage
            if 'code_type_inscription' not in df.columns:
                df.rename(columns={'type_formation': 'code_type_inscription'}, inplace=True)
                
            # Standardisation des valeurs (CLASSIQUE/HYBRIDE -> CLAS/HYB)
            # Utilisation de .loc pour éviter le SettingWithCopyWarning et s'assurer que c'est une chaîne
            df.loc[:, 'code_type_inscription'] = df['code_type_inscription'].astype(str).str.upper().replace({
                'CLASSIQUE': 'CLAS',
                'HYBRIDE': 'HYB'
            })
        
        # S'assurer que le nettoyage final est appliqué aux codes d'inscription et gérer les valeurs vides/NaN après le replace
        if 'code_type_inscription' in df.columns:
            df['code_type_inscription'] = df['code_type_inscription'].astype(str).apply(safe_string)

        # 🚨 AJOUT DE LA GARANTIE DE COLONNE 🚨
        if 'code_type_inscription' not in df.columns:
             # Si la colonne n'a jamais existé (ni type_formation, ni code_type_inscription)
             # On l'ajoute avec la valeur par défaut 'CLAS'
             df['code_type_inscription'] = 'CLAS'
             print("ℹ️ Colonne 'code_type_inscription' ajoutée avec la valeur par défaut 'CLAS'.")

        return df
        
    except Exception as e:
        print(f"❌ ERREUR: Impossible de lire ou de nettoyer le fichier d'inscriptions. {e}", file=sys.stderr)
        return None


def _import_annees_universitaires(session: Session, df: pd.DataFrame):
    """Importe les Années Universitaires."""
    print("\n--- Importation des Années Universitaires ---")
    if 'annee_universitaire' not in df.columns:
         print("Colonne 'annee_universitaire' manquante pour l'import des années universitaires.")
         return
         
    annees = df['annee_universitaire'].drop_duplicates().dropna()
    for annee in tqdm(annees, desc="Années Univ."):
        session.merge(AnneeUniversitaire(annee=safe_string(annee)))
    session.commit()
    print("✅ Années Universitaires insérées/mises à jour.")


def _import_etudiants(session: Session, df: pd.DataFrame):
    """Importe les Étudiants (commit par ligne)."""
    print("\n--- Importation des Étudiants (Ligne par Ligne FORCÉE) ---")
    
    # Nous conservons la suppression des doublons sur code_etudiant (clé primaire)
    df_etudiants = df.drop_duplicates(subset=['code_etudiant']).dropna(subset=['code_etudiant', 'nom'])
    etudiant_errors = 0
    
    for index, row in tqdm(df_etudiants.iterrows(), total=len(df_etudiants), desc="Import Etudiants"):
        code_etudiant = row.get('code_etudiant', 'N/A')
        
        try:
            naissance_date_val = row['naissance_date'] if isinstance(row['naissance_date'], date) else None
            cin_date_val = row['cin_date'] if isinstance(row['cin_date'], date) else None
            
            # Utilisation de safe_string partout pour assurer le nettoyage
            session.merge(Etudiant(
                code_etudiant=safe_string(code_etudiant), 
                numero_inscription=safe_string(row.get('numero_inscription')),
                nom=safe_string(row['nom']), 
                prenoms=safe_string(row['prenoms']),
                sexe=safe_string(row.get('sexe', 'Autre')), # Utilise 'Autre' ou valeur par défaut si absent pour le CheckConstraint
                naissance_date=naissance_date_val, 
                naissance_lieu=safe_string(row.get('naissance_lieu')),
                nationalite=safe_string(row.get('nationalite')),
                bacc_annee=int(row['bacc_annee']) if pd.notna(row['bacc_annee']) and row['bacc_annee'] is not None else None,
                bacc_serie=safe_string(row.get('bacc_serie')), 
                bacc_centre=safe_string(row.get('bacc_centre')),
                adresse=safe_string(row.get('adresse')), 
                telephone=safe_string(row.get('telephone')), 
                mail=safe_string(row.get('mail')),
                cin=safe_string(row.get('cin')), 
                cin_date=cin_date_val, 
                cin_lieu=safe_string(row.get('cin_lieu'))
            ))
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            etudiant_errors += 1
            e_msg = str(e.orig).lower() if hasattr(e, 'orig') and e.orig else str(e)
            
            print(f"❌ [ETUDIANT] Ligne Excel {row.name} ({code_etudiant}) - ERREUR: {e_msg.splitlines()[0]}")
            logging.error(f"ETUDIANT: {code_etudiant} | Erreur: {e_msg} | LIGNE_EXCEL_IDX: {row.name}")
            
    print(f"\n✅ Insertion des étudiants terminée. {etudiant_errors} erreur(s) individuelle(s) détectée(s).")


def _import_inscriptions(session: Session, df: pd.DataFrame):
    """Importe les Inscriptions (commit par lot)."""
    print("\n--- Importation des Inscriptions ---")
    
    cles_requises = ['code_inscription', 'code_etudiant', 'annee_universitaire', 'id_parcours', 'code_semestre', 'code_type_inscription']
    df_inscriptions = df.dropna(subset=cles_requises)
    
    errors_fk, errors_uq, errors_data, errors_other = 0, 0, 0, 0
    
    for index, row in tqdm(df_inscriptions.iterrows(), total=len(df_inscriptions), desc="Import Inscriptions"):
        code_inscription = row.get('code_inscription', 'N/A')
        
        try:
            session.merge(Inscription(
                code_inscription=safe_string(code_inscription), 
                code_etudiant=safe_string(row['code_etudiant']), 
                annee_universitaire=safe_string(row['annee_universitaire']), 
                id_parcours=row['id_parcours'], 
                code_semestre=safe_string(row['code_semestre']), 
                code_type_inscription=safe_string(row.get('code_type_inscription', 'CLAS')),
                # credit_acquis_semestre et is_semestre_valide ont des valeurs par défaut
            ))
            
            if (index + 1) % 500 == 0:
                session.commit()
                
        # Gestion des erreurs 
        except IntegrityError as e:
            session.rollback()
            e_msg = str(e.orig).lower()
            if "violates foreign key constraint" in e_msg: errors_fk += 1
            elif "violates unique constraint" in e_msg or "violates not null constraint" in e_msg: errors_uq += 1
            else: errors_other += 1
            
            logging.error(f"INSCRIPTION (Intégrité): {code_inscription} | Détail: {e.orig} | LIGNE_EXCEL_IDX: {row.name}")
        except DataError as e:
            session.rollback()
            errors_data += 1
            logging.error(f"INSCRIPTION (Données): {code_inscription} | Détail: {e.orig} | LIGNE_EXCEL_IDX: {row.name}")
        except Exception as e:
            session.rollback()
            errors_other += 1
            logging.error(f"INSCRIPTION (Autre): {code_inscription} | Erreur: {e} | LIGNE_EXCEL_IDX: {row.name}")
    
    try:
        session.commit()
        print("\n✅ Importation des inscriptions terminée.")
        print(f"\n--- Récapitulatif des erreurs d'insertion ---")
        print(f"Erreurs Clé Étrangère/Unique: {errors_fk + errors_uq}")
        print(f"Erreurs Format de Données: {errors_data}")
        print(f"Autres erreurs: {errors_other}")
        print(f"Voir 'import_errors.log' pour les détails complets.")
    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR CRITIQUE PENDANT LE COMMIT FINAL: {e}", file=sys.stderr)


# ----------------------------------------------------------------------
# FONCTION ORCHESTRATRICE DES INSCRIPTIONS
# ----------------------------------------------------------------------

def import_inscriptions_to_db():
    """
    Orchestre l'importation des données des étudiants et des inscriptions.
    """
    print(f"\n--- 3. Démarrage de l'importation des inscriptions et étudiants ---")
    
    # 🚨 VÉRIFICATION CRITIQUE: La fonction doit être appelée sans argument session 
    # si elle est définie comme telle, et le résultat vérifié immédiatement.
    df_inscriptions = _load_and_clean_inscriptions() 
    
    # === 🚨 AJOUT/VÉRIFICATION DU CONTRÔLE DE SÉCURITÉ (Guard Clause) 🚨 ===
    if df_inscriptions is None:
        print("❌ Importation des inscriptions annulée car le fichier de données est illisible ou corrompu.")
        return
    # =======================================================================
        
    session = database_setup.get_session()
    
    try:
        _import_annees_universitaires(session, df_inscriptions)
        _import_etudiants(session, df_inscriptions)
        _import_inscriptions(session, df_inscriptions)

    finally:
        session.close()


# ----------------------------------------------------------------------
# BLOC PRINCIPAL ET ORCHESTRATEUR GLOBAL
# ----------------------------------------------------------------------

def import_all_data():
    """
    Orchestre l'ensemble des étapes d'importation.
    """
    print("=====================================================")
    print("🚀 DÉMARRAGE DU PROCESSUS D'IMPORTATION DE DONNÉES 🚀")
    print("=====================================================")
    
    session = database_setup.get_session()
    
    try:
        import_fixed_references(session)
        
        session.commit()
        import_metadata_to_db() 
        
        session.commit()
        import_inscriptions_to_db()
        
        print("\n=====================================================")
        print("✅ IMPORTATION GLOBALE TERMINÉE AVEC SUCCÈS (ou erreurs loggées)")
        print("=====================================================")

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR FATALE dans l'orchestrateur principal: {e}", file=sys.stderr)
    finally:
        session.close()


if __name__ == '__main__':
    pass