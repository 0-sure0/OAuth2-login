###
# 필요한 라이브러리 및 모듈을 임포트한다.
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import urlencode
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx
from dotenv import load_dotenv
import os

# fastapi 앱 인스턴스 생성
app = FastAPI()
load_dotenv()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRETKEY"))

# Jinja2Templates 인스턴스를 생성하여 HTML 템플릿을 관리한다.
templates = Jinja2Templates(directory="templates")
#
# # 카카오에 애플리케이션을 등록할 때 받은 클라이언트 ID와 SECRET을 환경변수로부터 가져온다.
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_AUTHORIZATION_URL = os.getenv("KAKAO_AUTHORIZATION_URL")
KAKAO_TOKEN_URL = os.getenv("KAKAO_TOKEN_URL")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login")
async def login():
    query = urlencode({
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "response_type": "code",
    })
    kakao_login_url = f"{KAKAO_AUTHORIZATION_URL}?{query}"
    return RedirectResponse(url=kakao_login_url)


# 카카오 로그인을 위한 콜백 경로 설정 '/callback': 인증 코드를 받아 토큰을 요청한다.
@app.get("/callback")
async def kakao_callback(code: str, request: Request): # 카카오로부터 인증 코드를 받음
    # 토큰을 받아오기 위한 URL
    token_url = "https://kauth.kakao.com/oauth/token"

    headers = {
        "Content-type": "application/x-www-form-urlencoded;charset=utf-8"
    }

    # 요청 데이터를 구성한다.
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "client_secret": KAKAO_CLIENT_SECRET,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code
    }

    # 비동기 HTTP 클라이언트를 사용하여 토큰 요청을 보낸다.
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, headers=headers, data=data)
        response_json = response.json()

        # 응답에서 액세스 토큰을 가져온다.
        access_token = response_json.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="Access Token이 발급되지 않았습니다.")

    request.session['token'] = access_token

    # /welcome 경로로 리디렉션한다.
    return RedirectResponse(url="/welcome")


# 환영 페이지 경로 설정 '/welcome': 로그인 후 보여줄 페이지
@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    # 사용자 정보 요청 URL
    token = request.session.get('token')
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보 없음")

    user_info_url = "https://kapi.kakao.com/v2/user/me"

    # HTTP 헤더 구성
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-type": "application/x-www-form-urlencoded;charset=utf-8"
    }

    # 비동기 HTTP 클라이언트를 사용하여 사용자 정보 요청을 보낸다.
    async with httpx.AsyncClient() as client:
        response = await client.post(user_info_url, headers=headers)
        # 응답에서 사용자 정보를 가져온다.
        user_info = response.json()
    # 사용자 정보가 정상적으로 있는지 확인한다.

    if not user_info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="사용자 정보를 가져올 수 없습니다.")

    # welcome.html 페이지와 함께 사용자 정보를 반환한다.
    return templates.TemplateResponse("welcome.html", {"request": request, "user_info": user_info})


@app.get('/logout')
async def logout(request: Request):
    query = urlencode({
        "client_id": KAKAO_CLIENT_ID,
        "logout_redirect_uri": "http://localhost:8000/",
    })
    logout_url = f"https://kauth.kakao.com/oauth/logout?{query}"

    return RedirectResponse(url=logout_url)

