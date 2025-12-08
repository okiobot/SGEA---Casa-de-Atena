from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from .models import *
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.hashers import check_password 
from datetime import date, datetime
from decimal import Decimal
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
import random
from .serializers import *
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.mixins import CreateModelMixin
from rest_framework.authtoken.views import ObtainAuthToken
from email.mime.image import MIMEImage 

# Create your views here.
def home(request):
    return render(request, 'usuarios/home.html')

#Página de sobre------------------------------------------------------------------------------------------------------------

def sobre(request):
    # Adquire o ID e verifica se há algum, casa não haja, redireciona o usuário à tela de login
    usuario_id = request.session.get("usuario_id")

    if not usuario_id:
        return redirect("login")

    usuario = get_object_or_404(Usuario, id_usuario = usuario_id)    
    return render(request, "usuarios/sobre.html", {"usuario" : usuario})

#Funções envolvendo usuários------------------------------------------------------------------------------------------------------------

def deletar_usuario(request):
    usuario_id = request.session.get("usuario_id")

    if not usuario_id:
        return redirect("login")
    
    # Caso o método de acesso da página seja um GET, apenas será enviado os dados do usuário e a renderização da página
    if request.method == "GET":
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
        return render(request, "usuarios/deletar_usuario.html", {"usuario" : usuario})

    # Caso o método de acesso da página seja um POST, ele irá adquirir os dados do usuário e requerir uma senha, se a senha inserida for igual 
    # a senha anterior o perfil será deletado

    if request.method == "POST":
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
        senha = request.POST.get("senha")

        if not check_password(senha, usuario.password):
            return render(request, 'usuarios/deletar_usuario.html', {
                "usuario" : usuario,
                "toast_message": "Senha incorreta. Exclusão interrompida",
                "toast_type": "error",
            })
        
        # Adquire as informações, as registra e então deleta o usuário
        Registro.objects.create(usuario_id = usuario_id, acao = "Exclusão de usuário")
        usuario.delete()
        
        return redirect("cadastro")
        
def deletar_usuario_adm(request, usuario_id):
    user = Usuario.objects.filter(id_usuario = usuario_id)
    user.delete()

    return redirect("listagem_usuarios")

def cadastro_usuarios(request):
    # Adquire todas as informações inseridas pelo usuário
    if request.method == "POST":
        nome = request.POST.get("nome")
        sobrenome = request.POST.get("sobrenome")
        senha = request.POST.get("senha")
        telefone = request.POST.get("telefone")
        email = request.POST.get("email")
        instituicao = request.POST.get("ensi")
        tipo_usuario = request.POST.get("tipo")
        senha_tipo = request.POST.get("senha_acesso")
        confirmar_senha = request.POST.get("confirmar_senha")
        
        dados_preenchidos = {
            'nome_preenchido' : nome,
            'sobrenome_preenchido' : sobrenome,
            'senha_preenchida' : senha,
            'telefone_preenchido' : telefone,
            'email_preenchido' : email,
            'instituicao_preenchida' : instituicao,
            'tipo_usuario_preenchida' : tipo_usuario,
            'confirmar_senha_preenchida' : confirmar_senha
        }

        # Senhas de acesso para a criação de perfis de tipo 'professor' e 'organizador', respectivamente
        SENHAPROF = "123"
        SENHAORG = "321"
        
        # Verifica se o número inserido está conforme a regra definida (possuir 11 caracteres e apenas números)
        validatorE = RegexValidator(regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
        tamanhoT = len(telefone)
        telefone_arrumado = (f"({telefone[0:2]}) {telefone[2:7]}-{telefone[7:11]}")

        if not confirmar_senha == senha:
            return render(request, 'usuarios/home.html', {
                **dados_preenchidos,
                "toast_message": "As senhas são diferentes.",
                "toast_type": "error",
            })

        if len(senha) < 8:
            print(dados_preenchidos)
            return render(request, 'usuarios/home.html', {
                **dados_preenchidos,
                "toast_message": "As senha deve possuir 8 ou mais dígitos",
                "toast_type": "error",
            })

        if len(senha) >= 8:
            carac_especial = "@#$!%^&*()-+?_=,<>/\|."
            numeros = "0123456789"
            if any(c in carac_especial for c in senha):
                if any(c in numeros for c in senha):
                    pass
                else:
                    return render(request, 'usuarios/home.html', {
                        **dados_preenchidos,
                        "toast_message": "A senha deve possuir pelo menos um número.",
                        "toast_type": "error",
                    })
            else:
                return render(request, 'usuarios/home.html', {
                        **dados_preenchidos,
                        "toast_message": "A senha deve possuir pelo menos um caractere especial",
                        "toast_type": "error",
                    })
        else:
            return render(request, 'usuarios/home.html', {
                **dados_preenchidos,
                "toast_message": "A senha deve possuir no mínimo 8 caracteres.",
                 "toast_type": "error",
            })

        # Caso o número inserido não esteja no formato definido, esta mensagem irá aparecer ao usuário
        if not tamanhoT == 11:
            return render(request, 'usuarios/home.html', {
                **dados_preenchidos,
                "toast_message": "Número inserido de forma inválida, deve seguir o seguinte formato: '99999999999'.",
                 "toast_type": "error",
            })
        try:
            validatorE(email)
        # Caso o email inserido não esteja no formato definido, esta mensagem irá aparecer ao usuário
        except Exception:
            return render(request, 'usuarios/home.html', {
                **dados_preenchidos,
                "toast_message": "Email inserido de forma inválida, deve seguir o seguinte modelo: exemplo@exemplo.com",
                 "toast_type": "error",
            })
        
        # Caso o telefone já tenha sido utilizado, o sistema impede de criar um novo usuário
        if Usuario.objects.filter(telefone = telefone).exists():
            return render(request, 'usuarios/home.html', {
                **dados_preenchidos,
                "toast_message": "Este telefone já foi cadastrado.",
                 "toast_type": "error",
            })

        # Se todas as informações são válidas, um novo usuário é criado
        if tipo_usuario == "professor":
            if senha_tipo != SENHAPROF:
                return render(request, 'usuarios/home.html', {
                    **dados_preenchidos,
                    "toast_message": "Senha do professor inválida. Cadastro negado.",
                    "toast_type": "error",
                })

                    
        elif tipo_usuario == "organizador":
            if senha_tipo != SENHAORG:
                return render(request, 'usuarios/home.html', {
                    **dados_preenchidos,
                    "toast_message": "Senha do organizador inválida. Cadastro negado.",
                    "toast_type": "error",
                })

        
        if Usuario.objects.filter(email = email).exists():
            return render(request, 'usuarios/home.html', {
                **dados_preenchidos,
                "toast_message": "Este email já foi cadastrado.",
                 "toast_type": "error",
            })

        
        # Gerador de código que escolhe entre 10 números aleatórios e 26 letras aleatórias
        # O usuário pode escolher entrar com o código disponibilizado ou com a senha criada anteriormente
        codigo = ""
        for i in range(0,3):
            num = random.randint(0,9)
            let = random.choice("abcdefghijklmnopqrstuvwxyz")
            codigo += str(num)
            codigo += let
       
        # Caso todas as informações sejam inseridas corretamente, um novo usuário é criado 
        novo_usuario = Usuario.objects.create(nome = nome, sobrenome = sobrenome, telefone = telefone_arrumado, email = email, instituicao = instituicao, tipo = tipo_usuario, codigo = codigo)
        novo_usuario.set_password(senha)
        novo_usuario.save()

        logo_path = settings.BASE_DIR / 'login' / 'static' / 'assets' / 'logos' / 'atena_logo.png'

        emailhtml = render_to_string('usuarios/confirmacao_cadastro.html', {"usuario" : novo_usuario, "codigo" : codigo})

        try:
            email = EmailMultiAlternatives(subject=f"Confirmação de cadastro: {novo_usuario.nome} {novo_usuario.sobrenome}", 
                                body= emailhtml, from_email="casa.de.atenaa@gmail.com", to=[novo_usuario.email])
            email.content_subtype = 'html'

            with open(logo_path, 'rb') as f:
                logo_data = f.read()
            
            logo = MIMEImage(logo_data)
            logo.add_header('Content-ID', '<logo_cid>')
            logo.add_header('Content-Disposition', 'inline')
            email.attach(logo)
            
            email.attach_alternative(emailhtml, "text/html")
            
            email.send()
            
        except Exception:
            print("Erro ao enviar confirmação pelo email")
        
        Registro.objects.create(usuario_id = novo_usuario.id_usuario, acao = "Cadastro de usuário" )

        return redirect("login")
       
    return render(request, "usuarios/home.html")

def ver_usuarios(request):
    # Adquire o ID e verifica se há algum, casa não haja, redireciona o usuário à tela de login
    usuario_id = request.session.get("usuario_id")

    if not usuario_id:
        return redirect("login")
    
    try:
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
    
    except Usuario.DoesNotExist:
        return HttpResponse("Usuário não foi encontrado.")
    
    # Como está é uma página restrita a organizadores, caso uma pessoa já logada como 'estudante' ou 'professor' tente realizar o acesso a está página,
    # o sistema irá verificar o tipo do perfil, caso seja diferente de 'organizador', irá redirecionar o usuário a sua tela principal
    if usuario.tipo != "organizador":
        return redirect("inscricao")
    
    usuarios = {
    'usuarios' : Usuario.objects.all(),
    }  
    
    return render(request, 'usuarios/usuarios.html', usuarios)

def loginU(request):
    if request.method == "POST":
        email = request.POST.get("email")
        inputS = request.POST.get("senha") 

        dados_preenchidos = {
            'email_preenchido' : email,
            'senha_preenchida' : inputS
        }

        if not email or not inputS:
            messages.error(request, 'Insira um email e senha válidos.')
            return redirect('login')

        user = authenticate(request, username=email, password=inputS) 
        
        if user is None:
            try:
                user = Usuario.objects.get(email=email, codigo=inputS)
            except Usuario.DoesNotExist:
                user = None 

        if user is not None:
            
            # Login do usuário pelo Django
            login(request, user) 
            request.session["usuario_id"] = user.id_usuario
            return redirect("inscricao") 
        else:
            try:
                Usuario.objects.get(email=email)
                return render(request, 'usuarios/login.html', {
                    **dados_preenchidos,
                    "toast_message": "Usuário ou senha incorreta.",
                    "toast_type": "error",
                })
                
            except Usuario.DoesNotExist:
                return render(request, 'usuarios/login.html', {
                    **dados_preenchidos,
                    "toast_message": "Usuário não encontrado.",
                    "toast_type": "error",
                })
        
    return render(request, "usuarios/login.html")

def editar_usuario(request):
    usuario_id = request.session.get("usuario_id")
    
    if not usuario_id:
        redirect("login")
    
    usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
    
    if request.method == "POST":
        nome = request.POST.get("nome")
        senha = request.POST.get("senha")
        sobrenome = request.POST.get("sobrenome")
        telefone = request.POST.get("telefone")
        
        telefone_d = (usuario.telefone)
        telefone_desarrumado = f"{telefone_d[1]}{telefone_d[2]}{telefone_d[5:10]}{telefone_d[11:]}"
        usuario.telefone = telefone_desarrumado
        telefone_arrumado = (f"({telefone[0:2]}) {telefone[2:7]}-{telefone[7:11]}")
        
        if Usuario.objects.filter(telefone = telefone_arrumado).exclude(id_usuario = usuario_id):
            return render(request, 'usuarios/editar_usuario.html',
                {
                    "usuario": usuario,              
                    "toast_message": "Este telefone já foi cadastrado.",
                    "toast_type": "error",
                }
            )
        
        if len(senha) < 8:
            return render(request, 'usuarios/editar_usuario.html',
                {
                    "usuario": usuario,              
                    "toast_message": "As senha deve possuir 8 ou mais dígitos",
                    "toast_type": "error",
                }
            )
        else:
            carac_especial = "@#$!%^&*()-+?_=,<>/\|."
            numeros = "0123456789"
            if any(c in carac_especial for c in senha):
                if any(c in numeros for c in senha):
                    pass
                else:
                    return render(request, 'usuarios/editar_usuario.html',
                        {
                            "usuario": usuario,              
                            "toast_message": "A senha deve possuir ao menos um número.",
                            "toast_type": "error",
                        }
                    )
            else:
                return render(request, 'usuarios/editar_usuario.html',
                    {
                        "usuario": usuario,              
                        "toast_message": "A senha deve possuir ao menos um caracter especial.",
                        "toast_type": "error",
                    }
                )

        tamanho = len(telefone)
        
        if tamanho == 11:
            pass
        else:
            telefone_d = (usuario.telefone)
            telefone_desarrumado = f"{telefone_d[1]}{telefone_d[2]}{telefone_d[5:10]}{telefone_d[11:]}"
            usuario.telefone = telefone_desarrumado

            return render(request, 'usuarios/editar_usuario.html',
                {
                    "usuario": usuario,              
                    "toast_message": "O número deve ser inserido no seguinte formato: 9999999999999.",
                    "toast_type": "error",
                }
            )
        
        Registro.objects.create(usuario_id = usuario_id, acao = "Edição de perfil")
        
        # Caso as informações sejam inseridas corretamente, as mudanças são salvas
        usuario.nome = nome
        usuario.set_password(senha)
        usuario.telefone = telefone_arrumado
        usuario.sobrenome = sobrenome
        usuario.save()
    
        return redirect("inscricao")

    telefone_d = (usuario.telefone)
    telefone_desarrumado = f"{telefone_d[1]}{telefone_d[2]}{telefone_d[5:10]}{telefone_d[11:]}"
    usuario.telefone = telefone_desarrumado

    return render(request, "usuarios/editar_usuario.html", {"usuario" : usuario})

#Funções envolvendo eventos------------------------------------------------------------------------------------------------------------

def todos_eventos(request):
    usuario_id = request.session.get("usuario_id")
    
    if not usuario_id:
        return redirect("login")
      
    try:
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
    
    except Usuario.DoesNotExist:
        return HttpResponse("Usuário não foi encontrado.")
    
    if usuario.tipo != "organizador":
        return redirect("inscricao")
    
    eventos = {
        "eventos" : Evento.objects.all().order_by('emitido')
    }
    
    return render(request, "usuarios/visu_eventos.html", eventos)

def eventos(request):
    if request.method == 'POST':
        try:
            # Validação das informações adquiridas no campo das datas
            dia_inicio_str = request.POST.get("dataI")
            dia_fim_str = request.POST.get("dataF")

            ass = request.POST.get("assinatura")

            dia_inicio = datetime.strptime(dia_inicio_str, "%Y-%m-%d").date()
            dia_fim = datetime.strptime(dia_fim_str, "%Y-%m-%d").date()

            # Validação das informações adquiridas no campo dos horários
            horarioI_str = request.POST.get("horarioI")
            horarioF_str = request.POST.get("horarioF")
            horario_inicio = datetime.strptime(horarioI_str, "%H:%M").time()
            horario_final = datetime.strptime(horarioF_str, "%H:%M").time()
            

            # Cria um objeto datetime com uma data de placeholder e o horário definido pelo usuário
            datetime_inicio = datetime.combine(date.min, horario_inicio)
            datetime_final = datetime.combine(date.min, horario_final)
        
            # Duração do evento      
            duracao_timedelta = datetime_final - datetime_inicio
                    
            # Duração do evento em segundos
            total_segundos = duracao_timedelta.total_seconds()
            
            # Horas do evento, sem conter resto, sendo um número inteiro
            horas_inteiras = total_segundos // 3600
            
            # Segundos do evento, adquirindo o total possível divido por 3600
            segundos_restantes = total_segundos % 3600
            
            # Resto dos minutos, arredondando para baixo
            minutos_restantes = round(segundos_restantes / 60)
            
            minutos_decimal = minutos_restantes / 100.0
            horasC = Decimal(horas_inteiras) + Decimal(f"{minutos_decimal:.2f}")
            horasinp = request.POST.get("horas")
            if horasinp:
                try:
                    horas = Decimal(horasinp)
            
                except ValueError:
                    horas = horasC
            
            else:
                horas = horasC
            
            # Validação das informações adquiridas no campo das vagas
            vagas_str = request.POST.get("vagas")
            vagasInt = int(vagas_str)
            quantParticipantes_str = request.POST.get("quantPart")
            quantParticipantesInt = int(quantParticipantes_str)

            # Informações adquiridas e tratadas para serem corretamente utilizadas
            prof_id_str = request.POST.get("profOrg")
            prof_id = int(prof_id_str)
            prof_selecionado = get_object_or_404(Usuario, id_usuario=prof_id)
            prof_organizador = f"{prof_selecionado.nome} {prof_selecionado.sobrenome}"
            
            imagem = request.FILES.get("imagem")

            profs = Usuario.objects.filter(tipo = 'professor')

            dados_preenchidos = {
                'nomep' : request.POST.get('nome'),
                'tipoeventop' : request.POST.get('tipoE'),
                'dataIp' : request.POST.get('dataI'),
                'dataFp' : request.POST.get('dataF'),
                'horarioIp' : request.POST.get('horarioI'),
                'horarioFp' : request.POST.get('horarioF'),
                'localp' : request.POST.get('local'),
                'quantPartp' : request.POST.get('quantPart'),
                'organRespp' : request.POST.get('profOrg'),
                'vagasp' : request.POST.get('vagas'),
                'assinaturap' : request.POST.get('assinatura'),
                'horasp' : request.POST.get('horas'),
                'imagemp' : request.POST.get('imagem'),
                'descricaop' : request.POST.get('descricao'),
                'profs' : profs 
            }

            # Verifica se os espaços dos dias não estão vazios
            if not dia_inicio_str or not dia_fim_str:  
                return HttpResponse("O campo data de início e final são obrigatórios")

            try:
                # Define a forma que a data deve ser inserida para criar a string, .date() é utilizado para adquirir apenas a parte da data
                dia_inicio = datetime.strptime(dia_inicio_str, "%Y-%m-%d").date()
                dia_fim = datetime.strptime(dia_fim_str, "%Y-%m-%d").date()
                
            except ValueError:
                return HttpResponse("Formatação da data inválido, use: 'dia-mes-ano'.")
    
            #data_hj = timezone.now().date()
    
            if dia_fim < dia_inicio:
                return render(request, 'usuarios/eventos.html', {
                    **dados_preenchidos,
                    "toast_message": "A data final não pode ser anterior à data inicial.",
                    "toast_type": "error",
                })

            #if dia_inicio < data_hj:
                return HttpResponse("A data de início não pode ser anterior à data atual.")
            
            # Verifica se os espaços não estão vazios
            if not horarioI_str or not horarioF_str:
                return HttpResponse("O campo do horário inicial e final são obrigatórios")
            
            try:
                # Define a forma que o horário deve ser inserido para criar 
                horario_inicio = datetime.strptime(horarioI_str, "%H:%M").time()
                horario_final = datetime.strptime(horarioF_str, "%H:%M").time()
            
            except ValueError:
                return HttpResponse("Formato de data inserido inválido.")
                
            # Verifica se os horários estão entre horários existentes (entre 0 ou 24 horas)
            if horario_final <= horario_inicio:
                return render(request, 'usuarios/eventos.html', {
                    **dados_preenchidos,
                    "toast_message": "O horário final não pode ser anterior ao inicial.",
                    "toast_type": "error",
                })
            
            # Verifica se a informação adquirida é um número inteiro
            try:
                vagasInt = int(vagas_str)
            except ValueError:
                return render(request, 'usuarios/eventos.html', {
                    **dados_preenchidos,
                    "toast_message": "O valor das vagas deve ser um número inteiro positivo",
                    "toast_type": "error",
                })
            
            try:
                quantParticipantesInt = int(quantParticipantes_str)
            except ValueError:
                return render(request, 'usuarios/eventos.html', {
                    **dados_preenchidos,
                    "toast_message": "O valor da quantidade de participantes deve ser um valor inteiro positivo",
                    "toast_type": "error",
                })
            
            # Verifica se há uma quantidade maior de vagas do que de participantes
            if vagasInt > quantParticipantesInt:
                return render(request, 'usuarios/eventos.html', {
                    **dados_preenchidos,
                    "toast_message": "Não pode haver um número maior de vagas do que de participantes",
                    "toast_type": "error",
                })
            
            # Verifica se os valores são positivos
            if quantParticipantesInt < 0:
                return render(request, 'usuarios/eventos.html', {
                    **dados_preenchidos,
                    "toast_message": "Não pode haver uma quantidade negativa de participantes",
                    "toast_type": "error",
                })
            
            if vagasInt < 0:
                return render(request, 'usuarios/eventos.html', {
                    **dados_preenchidos,
                    "toast_message": "O valor das vagas deve ser um número inteiro positivo",
                    "toast_type": "error",
                })
            
            

            # Caso todas as informações sejam verificadas, um novo evento é criado
            novo_evento = Evento.objects.create(
            nome = request.POST.get("nome"),
            tipoevento = request.POST.get("tipoE"),
            dataI = dia_inicio,
            dataF = dia_fim,
            horarioI = horario_inicio,
            horarioF = horario_final,
            local = request.POST.get("local"),
            quantPart = quantParticipantesInt,
            organResp = prof_organizador,
            vagas = vagasInt,
            assinatura = ass,
            horas = horas,
            imagem = imagem,
            descricao = request.POST.get("descricao")
            )
            
            Registro.objects.create(evento_id = novo_evento.id_evento, acao = "Criação de evento")
            novo_evento.save()    
        
        except ValueError:
            messages.error(request, "Erro")
            return redirect("visu_eventos")
        
        eventos = {
            'eventos' : Evento.objects.all(),
        }

        return render(request, 'usuarios/visu_eventos.html', eventos)

def ev(request):
    usuario_id = request.session.get("usuario_id")
    
    if not usuario_id:
        return redirect("login")
      
    try:
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
    
    except Usuario.DoesNotExist:
        return HttpResponse("Usuário não foi encontrado.")
    
    if usuario.tipo != "organizador":
        return redirect("inscricao")
    
    profs = Usuario.objects.filter(tipo='professor')
    
    conteudo = {
        "usuarios" : usuario,
        "profs" : profs
    }
    
    print(conteudo)
    return render(request, "usuarios/eventos.html", conteudo)

def deletar_evento(request, pk):
    usuario_id = request.session.get("usuario_id")
    
    if not usuario_id:
        return redirect("login")
      
    try:
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
    
    except Usuario.DoesNotExist:
        return HttpResponse("Usuário não foi encontrado.")
    
    if usuario.tipo != "organizador":
        return redirect("inscricao")
    
    evento = get_object_or_404(Evento, pk = pk)
    
    Registro.objects.create(evento_id = pk, acao = "Exclusão de evento")
    
    evento.delete()
    return redirect("ver_certs")

def editar_evento(request, pk):
    usuario_id = request.session.get("usuario_id")
    
    if not usuario_id:
        return redirect("login")
      
    try:
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
    
    except Usuario.DoesNotExist:
        return HttpResponse("Usuário não foi encontrado.")
    
    if usuario.tipo != "organizador":
        return redirect("inscricao")
    
    evento = get_object_or_404(Evento, pk = pk)

    if request.method == "POST":
        nome = request.POST.get("nome")
        tipoevento = request.POST.get("tipo_evento")
        dataI_str = request.POST.get("dataI")
        dataF_str = request.POST.get("dataF")
        horarioI_str = request.POST.get("horarioI")
        horarioF_str = request.POST.get("horarioF")
        local = request.POST.get("local")
        quantPart_str = request.POST.get("quantPart")
        organResp = request.POST.get("organResp")
        vagas_str = request.POST.get("vagas")
        assinatura = request.POST.get("assinatura")
        horasinp = request.POST.get("horas")
        descricao = request.POST.get("descricao")
        
        try:
            if nome and tipoevento and dataI_str and dataF_str and horarioI_str and horarioF_str and local and quantPart_str and organResp and vagas_str and descricao:
                dataI = datetime.strptime(dataI_str, "%Y-%m-%d").date()
                dataF = datetime.strptime(dataF_str, "%Y-%m-%d").date()
                vagas = int(vagas_str)
                quantPart = int(quantPart_str)
                horarioI = datetime.strptime(horarioI_str, "%H:%M").time()
                horarioF = datetime.strptime(horarioF_str, "%H:%M").time()
                
                datetime_inicio = datetime.combine(date.min, horarioI)
                datetime_final = datetime.combine(date.min, horarioF)
                duracao_timedelta = datetime_final - datetime_inicio
                        
                total_segundos = duracao_timedelta.total_seconds()
                horas_inteiras = total_segundos // 3600                  
                segundos_restantes = total_segundos % 3600                   
                minutos_restantes = round(segundos_restantes / 60)
                minutos_decimal = minutos_restantes / 100.0              
                horasC = Decimal(horas_inteiras) + Decimal(f"{minutos_decimal:.2f}")

                horasinp = request.POST.get("horas")
                if horasinp:
                    try:
                        horas = Decimal(horasinp)
                
                    except ValueError:
                        horas = horasC
                
                else:
                    horas = horasC
                   
                if quantPart == 0:
                    return HttpResponse("Um evento não pode ter 0 participantes.")
                
                if quantPart < 0:
                    return HttpResponse("O evento não pode possuir um número negativo de participantes.")
            
                if dataI > dataF:
                    return HttpResponse("A data inicial não pode ser depois da data final.")

                if vagas > quantPart:
                    return HttpResponse("Não pode haver uma quantidade maior de vagas do que de participantes.")
            
                if horarioI > horarioF:
                    return HttpResponse("O horário inicial não pode ser menor que o horário final.")
            
                Registro.objects.create(evento_id = pk, acao = "Edição de evento")
            
                if not assinatura:
                    evento.assinatura = organResp
                
                else:
                    evento.assinatura = assinatura
                    
                evento.nome = nome
                evento.tipoevento = tipoevento
                evento.dataI = dataI
                evento.dataF = dataF
                evento.horarioI = horarioI
                evento.horarioF = horarioF
                evento.local = local
                evento.quantPart = quantPart
                evento.organResp = organResp
                evento.vagas = vagas
                evento.horas = horas
                evento.descricao = descricao
                evento.save()

                return redirect("even")

        except UnboundLocalError:
            return HttpResponse("Todas as caixas devem ser preenchidas.")

        else:
            return HttpResponse("Nenhum dos campos pode estar vazio.")

    return render(request, "usuarios/editar_evento.html", {"evento" : evento})

#Funções envolvendo inscrições------------------------------------------------------------------------------------------------------------

def home_inscricao(request):
    usuario_id = request.session.get("usuario_id")

    if not usuario_id:
        return redirect("login")

    usuario = Usuario.objects.get(id_usuario=usuario_id)
    eventos = Evento.objects.all()
    
    inscritos = Inscrito.objects.filter(usuario_id=usuario).values_list("evento_id", flat=True)

    return render(request, "usuarios/eventosU.html", {
        "usuario": usuario,
        "eventos": eventos,
        "inscritos": inscritos
    })

def inscricao_evento(request, usuario_id, evento_id):
    usuario_id = request.session.get("usuario_id")

    if not usuario_id:
        return redirect("login")
    
    if request.method == "POST":
        # Adquire o ID do usuário na sessão e o ID do evento selecionado 
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
        evento = get_object_or_404(Evento, id_evento = evento_id)
    
        # Cria uma nova inscrição e registra a inscrição nos logs
        nova_inscricao = Inscrito.objects.create(usuario_id = usuario, evento_id = evento)
        Registro.objects.create(usuario_id = nova_inscricao.usuario_id.id_usuario, evento_id = nova_inscricao.evento_id.id_evento, acao = "Inscrição em evento" )

        # Diminui a quantidade de vagas disponíveis
        evento.vagas -= 1
        evento.save()
        
        return redirect("inscricao")
           
    return render(request,"usuarios/meus_eventos.html", {"usuarios": Usuario.objects.all(), "eventos": Evento.objects.all()}) 

def sair_evento(request, usuario_id, evento_id):
    usuario = request.session.get("usuario_id")

    if not usuario:
        return redirect("login")
    
    if request.method == "GET":    
        evento = get_object_or_404(Evento, id_evento = evento_id)
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)

        if not Inscrito.objects.filter(usuario_id_id = usuario.id_usuario).exists():
            return HttpResponse('Usuário não está inscrito neste evento.')

        if not Inscrito.objects.filter(evento_id_id = evento.id_evento).exists():
            return HttpResponse('Evento não existe.')
                
        if Inscrito.objects.filter(evento_id_id = evento.id_evento, usuario_id_id = usuario.id_usuario):
            Inscrito.objects.filter(evento_id_id = evento.id_evento, usuario_id_id = usuario.id_usuario).delete()
            Registro.objects.create(usuario_id = usuario.id_usuario, evento_id = evento.id_evento, acao = "Saída de evento")

            evento.vagas += 1
            evento.save()
            
            return redirect("meus_eventos")
            
def usuario_eventos(request):
    usuario_id = request.session.get("usuario_id")

    if not usuario_id:
        return redirect("login")
    
    user = get_object_or_404(Usuario, id_usuario = usuario_id)
    inscricoes = Inscrito.objects.filter(usuario_id = user)
    
    eventos = [inscricao.evento_id for inscricao in inscricoes]
    
    return render(request, "usuarios/meus_eventos.html", {"usuario" : user, "eventos" : eventos})

#Funções envolvendo certificados------------------------------------------------------------------------------------------------------------

def ver_certificados(request):
    usuario_id = request.session.get("usuario_id")

    if not usuario_id:
        return redirect("login")
    
    user = get_object_or_404(Usuario, id_usuario = usuario_id)
    
    eventos = {
        'eventos' : Evento.objects.filter(emitido = False),
        'usuario' : user
    }
    
    return render(request, "usuarios/certificados.html", eventos)

def emitir_certificados(request):
    if request.method == 'POST':
        hoje = datetime.now()
        evento = Evento.objects.filter(emitido = False, dataF__lt = hoje)
        
        if not evento.exists():
            messages.info(request, "Nenhum evento elegível para emissão de certificados.")
            return redirect('ver_certs')
        
        for ev in evento:
            try:
                with transaction.atomic():
                    inscricoes = Inscrito.objects.filter(evento_id = ev.id_evento)

                    if not inscricoes.exists():
                        ev.emitido = True
                        ev.save()
                        messages.warning(request, f"AVISO!! Evento: {ev.nome} finalizado (sem inscrições).")
                        continue
                    
                    messages.info(request, "Seguintes eventos foram finalizados: ")
                    for inscricao in inscricoes:
                        nova_emissao = Certificado.objects.create(usuario_id = inscricao.usuario_id, evento_id = inscricao.evento_id, assinatura = inscricao.evento_id.assinatura, horas = inscricao.evento_id.horas_e_minutos)
                    
                    Inscrito.objects.filter(evento_id = ev.id_evento).delete()        
                    Registro.objects.create(usuario_id = nova_emissao.usuario_id.id_usuario, evento_id = nova_emissao.evento_id.id_evento, acao = "Emissão de certificado" )
                    
                    ev.emitido = True
                    ev.save()
                    messages.success(request, f"{ev.nome}")
            
            except Exception as e:
                return HttpResponse(f"Erro na emissão de certificados: {e}")
                
    return redirect("ver_certs")

def meus_certificados(request):
    usuario_id = request.session.get("usuario_id")
    
    try:
        usuario = get_object_or_404(Usuario, id_usuario = usuario_id)
        certs = Certificado.objects.filter(usuario_id = usuario)
    
    except Exception:
        return HttpResponse("Erro ao buscar certificados.")
    
    return render(request, "usuarios/meus_certificados.html", {"usuario" : usuario, "certificados" : certs})

#Deslogar---------------------------------------------------------------------------------------------------------

def logout(request):
    # Verifica se há um id de usuário armazenado na sessão, se houver, o deleta e redireciona o usuário para a tela de login
    if "usuario_id" in request.session:
        del request.session["usuario_id"]
    
    request.session.flush()
    
    return redirect("login")

#Registros---------------------------------------------------------------------------------------------------------

def registros(request):
    usuario_id = request.session.get("usuario_id")

    if not usuario_id:
        return redirect("login")
    
    # Adquire todos os registros e os organiza pela hora, de forma decrescente
    registros = {
        'registros' : Registro.objects.all().order_by("-hora")
    }
    
    return render(request, "usuarios/registros.html", registros)

#API---------------------------------------------------------------------------------------------------------

class CustomObtainAuthToken(ObtainAuthToken):
    serializer_class = CustomAuthTokenSerializer
    
class VerEventos(viewsets.ModelViewSet):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer
 
    permission_classes = []

    def list(self, request, *args, **kwargs):
        self.registro(request)  
        return super().list(request, *args, **kwargs)

    def registro(self, request):
        usuario = request.user

        if usuario.is_authenticated:
            Registro.objects.create(usuario_id=str(usuario.id_usuario), acao="Visualização de eventos pela API")
    
class InscricaoAPI(CreateModelMixin, viewsets.GenericViewSet):
    queryset = Inscrito.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = InscricaoAPISerializer
    
    def create(self, request, *args, **kwargs):
        usuario = request.user
        
        seri = InscricaoAPISerializer(data = request.data)
        
        if seri.is_valid():
            evento_id_api = seri.validated_data['id_evento']
            
            try:
                evento = Evento.objects.get(pk = evento_id_api)
                if Inscrito.objects.filter(usuario_id = usuario, evento_id = evento).exists():
                    print(evento.id_evento)
                    return Response({"detail" : "O usuário já está inscrito no evento."}, 
                                    status = status.HTTP_400_BAD_REQUEST)
            
                evento.vagas -= 1
                Registro.objects.create(usuario_id = usuario.id_usuario, evento_id = evento.id_evento, acao = "Inscrição em evento pela API")
                Inscrito.objects.create(usuario_id = usuario, evento_id = evento)
                
                return Response({"detail" : f"Usuário inscrito com sucesso no seguinte evento: {evento.nome}"},
                                status = status.HTTP_201_CREATED)
                
            except Evento.DoesNotExist:
                return Response({"detail" : f"O evento com o ID {evento.id_evento} específicado não existe"},
                                status = status.HTTP_404_NOT_FOUND)
                
        return Response(seri.errors, status = status.HTTP_400_BAD_REQUEST)
