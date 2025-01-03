from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, Count
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Student, Professor, Classe, Matiere, Cours, Note, Absence, Message, Payment, Rapport, UserProfile, Presence
from .forms import StudentForm, ProfessorForm, ClasseForm, MessageForm, PaymentForm, AbsenceForm, NoteForm, CoursForm
import uuid
import json
import time
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import os
from .forms import MatiereForm
