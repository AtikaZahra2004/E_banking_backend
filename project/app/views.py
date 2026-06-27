from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import BankAccount, Transaction
from decimal import Decimal
from .serializers import (
    RegisterSerializer,
    BankAccountSerializer,
    TransactionSerializer
)

# ───── REGISTER ─────
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Account created successfully!"},
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ───── DASHBOARD ─────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    try:
        account = BankAccount.objects.get(user=request.user)
        serializer = BankAccountSerializer(account)
        return Response(serializer.data)
    except BankAccount.DoesNotExist:
        return Response(
            {"error": "Bank account not found!"},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit(request):
    amount = request.data.get('amount')
    description = request.data.get('description', 'Deposit')

    if not amount or Decimal(str(amount)) <= 0:
        return Response(
            {"error": "Valid amount required!"},
            status=status.HTTP_400_BAD_REQUEST
        )

    account = BankAccount.objects.get(user=request.user)
    account.balance += Decimal(str(amount))  # ← float() ki jagah Decimal()
    account.save()

    Transaction.objects.create(
        account=account,
        transaction_type='DEPOSIT',
        amount=Decimal(str(amount)),
        description=description
    )

    return Response({
        "message": f"₹{amount} deposited successfully!",
        "new_balance": account.balance
    })
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw(request):
    amount = request.data.get('amount')
    description = request.data.get('description', 'Withdraw')

    if not amount or Decimal(str(amount)) <= 0:
        return Response(
            {"error": "Valid amount required!"},
            status=status.HTTP_400_BAD_REQUEST
        )

    account = BankAccount.objects.get(user=request.user)

    if account.balance < Decimal(str(amount)):
        return Response(
            {"error": "Insufficient balance!"},
            status=status.HTTP_400_BAD_REQUEST
        )

    account.balance -= Decimal(str(amount))  # ← fix
    account.save()

    Transaction.objects.create(
        account=account,
        transaction_type='WITHDRAW',
        amount=Decimal(str(amount)),
        description=description
    )

    return Response({
        "message": f"₹{amount} withdrawn successfully!",
        "new_balance": account.balance
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer(request):
    amount = request.data.get('amount')
    recipient_account_number = request.data.get('account_number')
    description = request.data.get('description', 'Transfer')

    if not amount or Decimal(str(amount)) <= 0:
        return Response(
            {"error": "Valid amount required!"},
            status=status.HTTP_400_BAD_REQUEST
        )

    sender_account = BankAccount.objects.get(user=request.user)

    if sender_account.balance < Decimal(str(amount)):
        return Response(
            {"error": "Insufficient balance!"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        recipient_account = BankAccount.objects.get(
            account_number=recipient_account_number
        )
    except BankAccount.DoesNotExist:
        return Response(
            {"error": "Recipient account not found!"},
            status=status.HTTP_404_NOT_FOUND
        )

    if sender_account == recipient_account:
        return Response(
            {"error": "Cannot transfer to your own account!"},
            status=status.HTTP_400_BAD_REQUEST
        )

    sender_account.balance -= Decimal(str(amount))
    sender_account.save()

    recipient_account.balance += Decimal(str(amount))
    recipient_account.save()

    Transaction.objects.create(
        account=sender_account,
        transaction_type='TRANSFER_SENT',
        amount=Decimal(str(amount)),
        description=f"Transfer to {recipient_account.user.username}"
    )
    Transaction.objects.create(
        account=recipient_account,
        transaction_type='TRANSFER_RECEIVED',
        amount=Decimal(str(amount)),
        description=f"Transfer from {sender_account.user.username}"
    )

    return Response({
        "message": f"₹{amount} transferred successfully!",
        "new_balance": sender_account.balance
    })
    # Sender se paisa nikalo
    sender_account.balance -= float(amount)
    sender_account.save()

    # Recipient ko paisa do
    recipient_account.balance += float(amount)
    recipient_account.save()

    # Dono ke liye transaction record
    Transaction.objects.create(
        account=sender_account,
        transaction_type='TRANSFER_SENT',
        amount=amount,
        description=f"Transfer to {recipient_account.user.username}"
    )
    Transaction.objects.create(
        account=recipient_account,
        transaction_type='TRANSFER_RECEIVED',
        amount=amount,
        description=f"Transfer from {sender_account.user.username}"
    )

    return Response({
        "message": f"₹{amount} transferred successfully!",
        "new_balance": sender_account.balance
    })


# ───── TRANSACTION HISTORY ─────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_history(request):
    account = BankAccount.objects.get(user=request.user)
    transactions = Transaction.objects.filter(
        account=account
    ).order_by('-timestamp')

    serializer = TransactionSerializer(transactions, many=True)
    return Response(serializer.data)