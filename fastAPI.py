import yfinance as yf
import models
from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from database import SessionLocal, engine
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models import Stock

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

class StockRequest(BaseModel):
    symbol: str

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

@app.get("/")
def home(request: Request, forward_pe = None, dividend_yield = None, ma50 = None, ma200 = None, db: Session = Depends(get_db)):
    # Display stock screen dashboard as homepage
    stocks = db.query(Stock)

    if forward_pe:
        stocks = stocks.filter(Stock.forward_pe < forward_pe)

    if dividend_yield:
        stocks = stocks.filter(Stock.dividend_yield > dividend_yield)

    if ma50 is not None:
        stocks = stocks.filter(Stock.price > ma50)

    if ma200 is not None:
        stocks = stocks.filter(Stock.price > ma200)
    
    return templates.TemplateResponse("home.html", {
        "request": request,
        "stocks": stocks,
        "dividend_yield": dividend_yield,
        "forward_pe": forward_pe,
        "ma50": ma50,
        "ma200": ma200
    })

def fetch_stock_data(id: int):
    db = SessionLocal()
    stock = db.query(Stock).filter(Stock.id == id).first()
    yf_data = yf.Ticker(stock.symbol)

    stock.ma200 = yf_data.info['twoHundredDayAverage']
    stock.ma50 = yf_data.info['fiftyDayAverage']
    stock.price = yf_data.info['previousClose']
    stock.forward_pe = yf_data.info['forwardPE']
    stock.forward_eps = yf_data.info['forwardEps']
    if yf_data.info['dividendYield'] is not None:
       stock.dividend_yield = yf_data.info['dividendYield'] * 100

    db.add(stock)
    db.commit()

@app.post("/stocks")
async def create_stocks(stock_request: StockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Create stock ticker and store data to database
    stock = Stock()
    stock.symbol = stock_request.symbol
    db.add(stock)
    db.commit()
    
    background_tasks.add_task(fetch_stock_data, stock.id)

    return {
        "code": "success",
        "message": "stock created"
    }