import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from database_manager import get_statistics

class StatsView:
    """Affiche les statistiques des rendez-vous"""
    
    def __init__(self, parent, user_id: int):
        self.frame = ttk.Frame(parent)
        self.user_id = user_id
        self.create_charts()
    
    def create_charts(self):
        """Crée les graphiques de statistiques"""
        stats = get_statistics(self.user_id)
        
        # Graphique 1 : Répartition par catégorie
        fig1 = plt.Figure(figsize=(6, 4), dpi=100)
        ax1 = fig1.add_subplot(111)
        
        categories = list(stats['categories'].keys())
        counts = list(stats['categories'].values())
        
        ax1.pie(
            counts,
            labels=categories,
            autopct='%1.1f%%',
            startangle=90,
            colors=['#FFCCBC', '#C5E1A5', '#81D4FA', '#FFF59D', '#E1BEE7', '#CFD8DC']
        )
        ax1.set_title("Répartition par catégorie")
        
        canvas1 = FigureCanvasTkAgg(fig1, master=self.frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Graphique 2 : Activité mensuelle
        fig2 = plt.Figure(figsize=(8, 3), dpi=100)
        ax2 = fig2.add_subplot(111)
        
        months = list(stats['monthly'].keys())
        values = list(stats['monthly'].values())
        
        ax2.bar(months, values, color='#4CAF50')
        ax2.set_title("Activité mensuelle")
        ax2.set_xlabel("Mois")
        ax2.set_ylabel("Nombre de RDVs")
        
        canvas2 = FigureCanvasTkAgg(fig2, master=self.frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Graphique 3 : Partages
        fig3 = plt.Figure(figsize=(6, 2), dpi=100)
        ax3 = fig3.add_subplot(111)
        
        shared_data = [
            stats['shared']['received'],
            stats['shared']['given']
        ]
        shared_labels = ["Reçus", "Donnés"]
        
        ax3.bar(shared_labels, shared_data, color=['#2196F3', '#FF9800'])
        ax3.set_title("Rendez-vous partagés")
        ax3.set_ylabel("Nombre")
        
        canvas3 = FigureCanvasTkAgg(fig3, master=self.frame)
        canvas3.draw()
        canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=10)