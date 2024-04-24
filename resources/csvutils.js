function loadStoreSheetAndMatchupSheet(store_name) {
    const camelCaseStoreName = store_name.replace(/(?:^\w|[A-Z]|\b\w)/g, function(word, index) {
        return index == 0 ? word.toLowerCase() : word.toUpperCase();
    }).replace(/\s+/g, '');
  $("#sheetModalLabel").text(camelCaseStoreName);
  $("#contents").empty();

  try {
    loadSheet('stores/' + store_name + '.csv');
  } catch (e) {
    $("#contents").html(
      '<div class="alert alert-danger">Error loading sheet: ' +
        e.message +
        "</div>",
    );
  }

  try {
    loadSheet('stores/' + store_name + '-matchups.csv', true);
  } catch (e) {
      console.log("No matchups sheet found for " + store_name + ".")
  }
}

function loadSheet(filename, isMatchup = false) {
  fetch(filename)
    .then((response) => response.blob())
    .then((text) => {
      // Read the file as text
      var reader = new FileReader();
      reader.onload = function (e) {
        var contents = e.target.result; // Parse local CSV file
        Papa.parse(contents, {
          header: true,
          dynamicTyping: true,
          complete: function (results) {
            for (result of results.data) {
              let header =
                result?.brand_name !== "N/A"
                  ? result?.brand_name
                  : result?.product_name;
              header = header
                ? header.replace(/\w\S*/g, function (txt) {
                    return (
                      txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
                    );
                  })
                : "Product Offer";
              let product =
                result?.brand_name !== "N/A" && result?.product_name
                  ? result?.product_name
                  : "";
              let description = result?.description
                ? `<div class="coupon-info">Description: ${result?.description}</div>`
                : "";
              let variety = result?.product_variety
                ? `<div class="coupon-info">Variety: ${result?.product_variety}</div>`
                : "";
              let price = result?.price
                ? `<div class="coupon-deal">Price/Savings: <span>$${result?.price}</span></div>`
                : "";
              let validFromTo = `<div class="coupon-validity">Valid: <span>${result?.valid_from} to ${result?.valid_to}</span></div>`;
              let requiresCard =
                result?.requires_store_card === 1
                  ? '<div class="coupon-requirements">Requires Store Card</div>'
                  : "";

              if (header === "None") {
                header = product;
              }

              var row = `
                    <div class="coupon-card">
                        ${isMatchup ? '<div class="coupon-matchup">Matchup</div>' : ''}
                        <div class="coupon-header">${header}</div>
                        ${header === product || product.length < 1 ? "" : `<small>${product}</small>`}
                        <br />
                        ${description}
                        ${variety}
                        ${price}
                        ${validFromTo}
                        ${requiresCard}
                        <div class="clear-both"></div>
                    </div>
                `;
              $("#contents").append(row);
            }
          },
        });
      };
      reader.readAsText(text);
    });
}
