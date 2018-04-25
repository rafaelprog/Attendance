
#####################################################################
#                                                                   #
#                                                                   #
#                                                                   #
#           Desenvolvido por: Rafael Rocha                          #
#                                                                   #
#                                                                   #
#                                                                   #
#                                                                   #
#####################################################################

from collections import deque
from odoo import models, fields, api
from odoo import os
from odoo.exceptions import UserError
import base64
from StringIO import StringIO
import sys
import tempfile
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class formmicro_arquivos(models.Model):
    
    #region module properties

    _name= "tb_ponto"
    enviado_por = fields.Many2one('res.users','Enviado Por', default=lambda self: self.env.user)
    data_upload = fields.Char('Data do Upload')
    registro = fields.Binary('Arquivo')
    
    #endregion
    
    @api.multi
    def importa_arquivo(self):

        self.data_upload = datetime.now()

        lines = self.ReadDocumentLines()
        self.FillEmployeePointDictionary(lines)

        self.CreateCoupleOfPoints()

        for pis , moviment in EmployeeMoviment.dictionary.iteritems():
            _logger.info("Pis: " + str(pis))
            while True:

                if len(moviment) > 0:
                    item = moviment.popleft()
                else:
                    break

                checkin = item.checkIn.strftime("%Y-%m-%d %H:%M:%S") 
                checkOut =  item.checkOut.strftime("%Y-%m-%d %H:%M:%S")
                createDate = item.createData.strftime("%Y-%m-%d %H:%M:%S")
                writeDate =  item.writeData.strftime("%Y-%m-%d %H:%M:%S")          
                _logger.info("Employee: " + str(item.employeeId) + "  CheckIn: " + str(checkin) + "  CheckOut "+ str(checkOut))

                if item.employeeId != "False" :     
                  
                    self.env['hr.attendance'].create({
                        'create_uid':'99',
                        'check_in': str(checkin),
                        'employee_id':int(item.employeeId), 
                        'worked_hours':str(item.workedHours),
                        'create_date': str(createDate),
                        'write_date': str(writeDate),
                        'check_out': str(checkOut),
                        'write_uid':'99',              
                        'sheet_id':1})    

                    self.env.cr.commit()
                    
                else:
                    continue     
      
    def ReadDocumentLines(self):

        arquivo = self.with_context({'bin_size': False}).registro
        temporario = base64.decodestring(arquivo)
        lines = temporario.rsplit("\n")[:-1]
        for line in lines: 
            _logger.info("linha :" + line)
    

        return lines
   
    def FillEmployeePointDictionary(self,lines):
        for line in lines: 
            employeePointInfo = self.CreateEmployeePoint(line)
            
            # loggerString = "FillEmployeePointDictionary: " + str(employeePointInfo.datePoint)
            # _logger.info(loggerString)
            self.InsertPointIntoDict(employeePointInfo)

    def CreateEmployeePoint(self,pointRegister):

        pointRegister = pointRegister.strip()
        marcacao = pointRegister[0:5]
        pis = pointRegister[5:8] + "." + pointRegister[8:13] + "." + pointRegister[13:15] + "." + pointRegister[15:16]
        data = pointRegister[16:18] + "/" + pointRegister[18:20] + "/" + pointRegister[20:24]     
        hora = pointRegister[24:26] +  ":" + pointRegister[26:28] +  ":00"
        employeeId = self.GetEmployeeByPis(pis)
        dateTime = data + ' ' + hora
        return EmployeePointInfo(employeeId,marcacao,pis,dateTime)

    def InsertPointIntoDict(self,PointInfo):
        #Verifica se o indice do pis existe no dicionario estatico
        #Caso não exista cria o indice e adiciona o primeiro ponto do pis
        #Caso exista apenas faz um append ao dicionario estatico no indice respectivo ao pis_pasep
        if PointInfo.pis in EmployeePointInfo.dictionary:
             EmployeePointInfo.dictionary[PointInfo.pis].append(PointInfo)
        else:
            EmployeePointInfo.dictionary[PointInfo.pis] = deque([PointInfo])
            
    def GetEmployeeByPis(self,pis):
        employeeId = self.env['hr.employee'].search([('pis_pasep', '=', pis)], limit=1).id
        return str(employeeId)
      
    def CreateCoupleOfPoints(self):

        for pis, employeePoints in EmployeePointInfo.dictionary.iteritems():
            while True:
                try:
                    if len(employeePoints) > 0:
                        checkInPoint = employeePoints.popleft()
                    else:
                        break
                   
                    if len(employeePoints) > 0:
                        checkOutPoint = employeePoints.popleft()
                        #raise UserError("checking date :" + str(checkInPoint.datePoint) + "checkout date :" + str(checkOutPoint.datePoint))   
                        self.JoinPoints(checkInPoint,checkOutPoint)
                    else:      
                        # loggerString = "CreateCoupleOfPoints Date: " + str(checkInPoint.datePoint)
                        # _logger.info(loggerString)                
                        self.CreateTemporaryCheckout(checkInPoint)
                        break

                except IndexError:
                    break

    def JoinPoints(self,checkInPoint,checkOutPoint):


        checkInDate = datetime.strptime(checkInPoint.datePoint, "%d/%m/%Y %H:%M:%S")
        checkOutDate = datetime.strptime(checkOutPoint.datePoint, "%d/%m/%Y %H:%M:%S")
        checkInDate = checkInDate + timedelta(hours=2) 
        checkOutDate = checkOutDate + timedelta(hours=2) 

        createDate = datetime.now()
        
        diff = checkOutDate - checkInDate
        days, seconds = diff.days, diff.seconds
        workedHours = days * 24.0 + seconds / 3600.0
    
        if workedHours > 12:
          
            self.CreateTemporaryCheckout(checkInPoint)
            self.GiveBackToDeque(checkOutPoint)
        else:         
            employeeMoviment = EmployeeMoviment(checkInPoint.employeeId, checkInPoint.pis, checkInDate,checkOutDate, createDate, createDate, workedHours)
            self.InsertEmployeeMovimentToDict(employeeMoviment)   

    def GiveBackToDeque(self,checkOutPoint):    
        EmployeePointInfo.dictionary[checkOutPoint.pis].appendleft(checkOutPoint)
        
    def CreateTemporaryCheckout(self,checkInPoint):
        #Caso o checkin e o checkout for maior que 12 horas conseder um checkout tempotario
        
        checkInDate = datetime.strptime(checkInPoint.datePoint, "%d/%m/%Y %H:%M:%S")
       

        checkInDate = checkInDate + timedelta(hours=2) 
        checkOutDate = checkInDate + timedelta(minutes=1) 

        createDate = datetime.now() + timedelta(hours=2)

        employeeMoviment = EmployeeMoviment(checkInPoint.employeeId, checkInPoint.pis, checkInDate,checkOutDate,createDate , createDate, 0)
        self.InsertEmployeeMovimentToDict(employeeMoviment)
        
    def InsertEmployeeMovimentToDict(self,employeeMoviment):
        if employeeMoviment.pis in EmployeeMoviment.dictionary:
            EmployeeMoviment.dictionary[employeeMoviment.pis].append(employeeMoviment)
        else:
            EmployeeMoviment.dictionary[employeeMoviment.pis] = deque([employeeMoviment])

class EmployeePointInfo:
    
    #Cria um dicionario estatico para classe
    #Dicionario para Chave (pis_pasep) e Deque(pontos daquele pis)

    dictionary = {}

    def __init__(self,employeeId,marcacao,pis,datePoint):

        self.employeeId = employeeId
        self.marcacao = marcacao
        self.pis = pis
        self.datePoint = datePoint    

class EmployeeMoviment:

    dictionary = {}

    def __init__(self, employeeId, pis, checkIn, checkOut, writeData, createData, workedHours):
        self.employeeId = employeeId
        self.pis = pis
        self.checkIn = checkIn
        self.checkOut = checkOut
        self.createId = 99
        self.writeId =  99
        self.writeData = writeData
        self.createData = createData
        self.workedHours = workedHours
        

        

       

      
    
    
  


    



