function empty() {

    localStorage.removeItem('cart');

    window.location.reload();

}

async function purchase(cart) {

    alert('You submitted a purchase attempt; please click OK and await the response.')

    let purchaseResponse = await fetch('/server/offering/purchases', {
        method: ['POST'],
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(cart)
    });

    if (!purchaseResponse.ok) {

        let purchaseReponseBody = await purchaseResponse.text();

        alert(`The server denied the purchase with the following error. ${purchaseReponseBody}`);

    } else {

        let purchase = await purchaseResponse.json();

        window.location.replace(purchase['url']);
    
    }

}

function main() {

    if (localStorage.getItem('cart') === null) {

        localStorage.setItem('cart', JSON.stringify([]));

    }

    let cartDiv = document.getElementById('cart');

    let cart = JSON.parse(localStorage.getItem('cart'));

    if (cart.length === 0) {

        cartDiv.className = 'flex-column-center';

        cartDiv.innerText = 'Your cart is empty.';

    } else {

        for (let offer of cart) {

            let div = document.createElement('div');

            div.setAttribute('style', 'margin-top: 10px;')

            div.innerText = offer['name'].concat(' - $', String(offer.price));

            cartDiv.appendChild(div);

        }

        emptyButton = document.createElement('button');

        emptyButton.className = 'light-button';

        emptyButton.setAttribute('style', 'font-size: 16px; height: 35px;');

        emptyButton.innerText = 'Empty cart';

        emptyButton.addEventListener('mouseup', ()=>{empty();});

        cartDiv.appendChild(emptyButton);

        purchaseButton = document.createElement('button');

        purchaseButton.className = 'dark-button';

        purchaseButton.setAttribute('style', 'font-size: 16px; height: 35px;');

        purchaseButton.innerText = 'Checkout';

        purchaseButton.addEventListener('mouseup', ()=>{purchase(cart);});

        cartDiv.appendChild(purchaseButton);

    }

}

main();
