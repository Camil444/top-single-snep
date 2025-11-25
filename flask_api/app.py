import os
import psycopg2
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from the root .env file
# Assuming the script is run from the root or we point to the root .env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('POSTGRES_DB', 'db'),
        user=os.getenv('POSTGRES_USER', 'db_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'db_password'),
        port=os.getenv('DB_PORT', '5432')
    )
    return conn

@app.route('/api/artist/<artist_name>', methods=['GET'])
def get_artist_stats(artist_name):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Construct the query to union all tables from 2020 to 2025
        years = range(2020, 2026) 
        
        union_parts = []
        for year in years:
            # Select producer columns to allow filtering by them
            union_parts.append(f"SELECT titre, classement, artiste, producer_1, producer_2 FROM top_singles_{year}")
            
        union_query = " UNION ALL ".join(union_parts)
        
        search_type = request.args.get('type', 'artist')
        
        if search_type == 'producer':
            where_clause = "(producer_1 ILIKE %s OR producer_2 ILIKE %s)"
            params = (f'%{artist_name}%', f'%{artist_name}%')
        else:
            where_clause = "artiste ILIKE %s"
            params = (f'%{artist_name}%',)
        
        query = f"""
            SELECT 
                titre,
                COUNT(*) as weeks_in_top,
                MIN(classement) as best_rank
            FROM ({union_query}) as all_years
            WHERE {where_clause}
            GROUP BY titre
            ORDER BY weeks_in_top DESC;
        """
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            results.append({
                'titre': row[0],
                'weeks_in_top': row[1],
                'best_rank': row[2]
            })
            
        cur.close()
        conn.close()
        
        return jsonify({
            'artist': artist_name,
            'songs': results,
            'total_songs': len(results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/privacy', methods=['GET'])
def privacy_policy():
    """
    GDPR: Right to be Informed.
    Returns the privacy policy and information about data processing.
    """
    return jsonify({
        "policy": "GDPR Compliance Statement",
        "controller": "SNEP Analytics Project",
        "data_processed": [
            "Artist Names (Public Data)",
            "Producer Names (Public Data)",
            "Song Titles",
            "Rankings"
        ],
        "legal_basis": "Legitimate Interest (Public availability of music charts)",
        "purpose": "Statistical analysis and historical archiving of music charts.",
        "data_retention": "Data is retained for the duration of the project lifecycle.",
        "user_rights": {
            "access": "GET /api/artist/<name> provides full access to stored data for an entity.",
            "portability": "Data is returned in standard JSON format.",
            "rectification_erasure": "Please contact camilhennebertpro@gmail.com for correction or deletion requests."
        },
        "contact": "camilhennebertpro@gmail.com"
    })

@app.route('/api/gdpr/export/<entity_name>', methods=['GET'])
def export_data(entity_name):
    """
    GDPR: Right to Data Portability.
    Allows exporting all data related to an entity in a machine-readable format.
    """
    # Re-use the existing logic but explicitly labeled for export
    return get_artist_stats(entity_name)

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Use 5001 to avoid conflict with dashboard on 3000 or airflow on 8080
