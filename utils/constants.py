modal_html = """<div class="modal" tabindex="-1"
             id="sheetModal" aria-labelledby="sheetModalLabel" aria-hidden="true">  <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="my-1" style="
                            display: flex;
                            width: 100%;
                            align-content: center;
                            flex-wrap: wrap;
                            align-items: center;
                            justify-content: center;
                            text-align: center;
                        ">
                        <div class="col-6 text-left">
                            <h5 id="sheetModalLabel"></h5>
                        </div>
                        <div class="col-6 text-right">
                            <button type="button" class="close" data-bs-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true"><i class="fa fa-times"></i></span>
                            </button>
                        </div>
                    </div>
                    <div class="row my-1">
                        <input type="text" id="search" placeholder="Search for a product..." class="form-control">
                        <div class="row mt-1 mx-auto">
                            <div class="col-6 text-center">
                                <button id="searchButton" class="btn btn-primary">Search</button>
                            </div>
                            <div class="col-6 text-center">
                                <button id="clearSearch" class="btn btn-secondary">Clear</button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-body">

                    <div id="contents"></div>
                </div>
            </div>
        </div>
        </div>"""

extra_script = """window.addEventListener('DOMContentLoaded', (event) => {
                $('#searchButton').click(function() {
                    var search = $('#search').val();
                    var cards = $('.coupon-card');
                    cards.each(function(index, card) {
                        var header = $(card).find('.coupon-header').text();
                        if (header.toLowerCase().includes(search.toLowerCase())) {
                            $(card).show();
                        } else {
                            $(card).hide();
                        }
                    });
                });

                $('#clearSearch').click(function() {
                    $('#search').val('');
                    var cards = $('.coupon-card');
                    cards.each(function(index, card) {
                        $(card).show();
                    });
                });
            });

            function findLeafletMap() {
                for (var key in window) {
                    if (key.startsWith('map_') && window[key] instanceof L.Map) {
                        return window[key];
                    }
                }
                return null;
            }

            const icons = {
                'turn-left': `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23000000' viewBox='0 0 24 24' id='turn-left-top-direction-circle' data-name='Flat Color' class='icon flat-color'%3E%3Ccircle id='primary' cx='12' cy='12' r='10' style='fill: rgb(0, 0, 0);'/%3E%3Cpath id='secondary' d='M13,9H10.41l.3-.29A1,1,0,1,0,9.29,7.29l-2,2a1,1,0,0,0,0,1.42l2,2a1,1,0,0,0,1.42,0,1,1,0,0,0,0-1.42l-.3-.29H13v5a1,1,0,0,0,2,0V11A2,2,0,0,0,13,9Z' style='fill: rgb(44, 169, 188);'/%3E%3Cscript xmlns='' id='bw-fido2-page-script'/%3E%3C/svg%3E"`,
                'turn-right': `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23000000' viewBox='0 0 24 24' id='turn-right-direction-circle' data-name='Flat Color' class='icon flat-color'%3E%3Ccircle id='primary' cx='12' cy='12' r='10' style='fill: rgb(0, 0, 0);'/%3E%3Cpath id='secondary' d='M16.71,9.29l-2-2a1,1,0,1,0-1.42,1.42l.3.29H11a2,2,0,0,0-2,2v5a1,1,0,0,0,2,0V11h2.59l-.3.29a1,1,0,0,0,0,1.42,1,1,0,0,0,1.42,0l2-2A1,1,0,0,0,16.71,9.29Z' style='fill: rgb(44, 169, 188);'/%3E%3C/svg%3E"`,
                'uturn': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M17.0005 18.1716L14.4649 15.636L13.0507 17.0503L18.0005 22L22.9502 17.0503L21.536 15.636L19.0005 18.1716V11C19.0005 6.58172 15.4187 3 11.0005 3C6.58218 3 3.00046 6.58172 3.00046 11V20H5.00046V11C5.00046 7.68629 7.68675 5 11.0005 5C14.3142 5 17.0005 7.68629 17.0005 11V18.1716Z'%3E%3C/path%3E%3C/svg%3E",
                'exit-left': "data:image/svg+xml,%3Csvg fill='%23000000' viewBox='0 0 24 24' id='up-left-arrow-circle' data-name='Flat Color' xmlns='http://www.w3.org/2000/svg' class='icon flat-color'%3E%3Ccircle id='primary' cx='12' cy='12' r='10' style='fill: rgb(0, 0, 0);'%3E%3C/circle%3E%3Cpath id='secondary' d='M7.24,8.21l.7,3.73a1,1,0,0,0,1.55.57l.8-.8,4.54,4.53a1,1,0,0,0,1.41,0,1,1,0,0,0,0-1.41l-4.53-4.54.8-.8a1,1,0,0,0-.57-1.55l-3.73-.7A.82.82,0,0,0,7.24,8.21Z' style='fill: rgb(44, 169, 188);'%3E%3C/path%3E%3C/svg%3E",
                'exit-right': "data:image/svg+xml,%3Csvg fill='%23000000' viewBox='0 0 24 24' id='up-right-arrow-circle' data-name='Flat Color' xmlns='http://www.w3.org/2000/svg' class='icon flat-color'%3E%3Ccircle id='primary' cx='12' cy='12' r='10' style='fill: rgb(0, 0, 0);'%3E%3C/circle%3E%3Cpath id='secondary' d='M15.79,7.24l-3.73.7a1,1,0,0,0-.57,1.55l.8.8L7.76,14.83a1,1,0,0,0,0,1.41,1,1,0,0,0,1.41,0l4.54-4.53.8.8a1,1,0,0,0,1.55-.57l.7-3.73A.82.82,0,0,0,15.79,7.24Z' style='fill: rgb(44, 169, 188);'%3E%3C/path%3E%3C/svg%3E",
                'store': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M21 11.6458V21C21 21.5523 20.5523 22 20 22H4C3.44772 22 3 21.5523 3 21V11.6458C2.37764 10.9407 2 10.0144 2 9V3C2 2.44772 2.44772 2 3 2H21C21.5523 2 22 2.44772 22 3V9C22 10.0144 21.6224 10.9407 21 11.6458ZM14 9C14 8.44772 14.4477 8 15 8C15.5523 8 16 8.44772 16 9C16 10.1046 16.8954 11 18 11C19.1046 11 20 10.1046 20 9V4H4V9C4 10.1046 4.89543 11 6 11C7.10457 11 8 10.1046 8 9C8 8.44772 8.44772 8 9 8C9.55228 8 10 8.44772 10 9C10 10.1046 10.8954 11 12 11C13.1046 11 14 10.1046 14 9Z'%3E%3C/path%3E%3C/svg%3E",
                'compass': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='currentColor'%3E%3Cpath d='M12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12C22 17.5228 17.5228 22 12 22ZM12 20C16.4183 20 20 16.4183 20 12C20 7.58172 16.4183 4 12 4C7.58172 4 4 7.58172 4 12C4 16.4183 7.58172 20 12 20ZM15.5 8.5L13.5 13.5L8.5 15.5L10.5 10.5L15.5 8.5Z'%3E%3C/path%3E%3C/svg%3E",
                'straight': `data:image/svg+xml,%3Csvg fill='%23000000' viewBox='0 0 24 24' id='up-direction-square' data-name='Flat Color' xmlns='http://www.w3.org/2000/svg' class='icon flat-color'%3E%3Crect id='primary' x='2' y='2' width='20' height='20' rx='2' style='fill: rgb(0, 0, 0);'%3E%3C/rect%3E%3Cpath id='secondary' d='M14,12v4a1,1,0,0,1-1,1H11a1,1,0,0,1-1-1V12H9.18a1,1,0,0,1-.76-1.65l2.82-3.27a1,1,0,0,1,1.52,0l2.82,3.27A1,1,0,0,1,14.82,12Z' style='fill: rgb(44, 169, 188);'%3E%3C/path%3E%3C/svg%3E`,
                'roundabout': `data:image/svg+xml,%3Csvg fill='%23000000' viewBox='0 0 24 24' id='update' data-name='Flat Color' xmlns='http://www.w3.org/2000/svg' class='icon flat-color'%3E%3Cpath id='primary' d='M19,2a1,1,0,0,0-1,1V5.33A9,9,0,0,0,3,12a1,1,0,0,0,2,0A7,7,0,0,1,16.86,7H14a1,1,0,0,0,0,2h5a1,1,0,0,0,1-1V3A1,1,0,0,0,19,2Z' style='fill: rgb(0, 0, 0);'%3E%3C/path%3E%3Cpath id='secondary' d='M20,11a1,1,0,0,0-1,1A7,7,0,0,1,7.11,17H10a1,1,0,0,0,0-2H5a1,1,0,0,0-1,1v5a1,1,0,0,0,2,0V18.67A9,9,0,0,0,21,12,1,1,0,0,0,20,11Z' style='fill: #000000;'%3E%3C/path%3E%3C/svg%3E`
            }

            function mapDirectionToFontAwesome(direction) {
                direction = direction.toLowerCase();
                if (direction.includes('exit left') || direction.includes('keep left')) {
                    return 'exit-left';
                } else if (direction.includes('exit right') || direction.includes('keep right')) {
                    return 'exit-right';
                } else if (direction.includes('roundabout')) {
                    return 'roundabout';
                } else if (direction.includes('straight')) {
                    return 'straight';
                } else if (direction.includes('uturn')) {
                    return 'uturn';
                } else if (direction.includes('destination') || direction.includes('arrive')) {
                    return 'store';
                } else if (direction.includes('head')) {
                    return 'compass';
                } else if (direction.includes('turn left') || direction.includes('sharp left') || direction.includes('left')) {
                    return 'turn-left'
                } else if (direction.includes('turn right') || direction.includes('sharp right') || direction.includes('right')) {
                    return 'turn-right';
                } else {
                    return 'compass'
                }
            }

            function secondsToHms(d) {
                d = Number(d);
                var h = Math.floor(d / 3600);
                var m = Math.floor(d % 3600 / 60);
                var s = Math.floor(d % 3600 % 60);

                var hDisplay = h > 0 ? h + (h === 1 ? " hour, " : " hours, ") : "";
                var mDisplay = m > 0 ? m + (m === 1 ? " minute, " : " minutes, ") : "";
                var sDisplay = s > 0 ? s + (s === 1 ? " second" : " seconds") : "";

                const out = hDisplay + mDisplay + sDisplay;
                return out.length > 0 ? out : 'N/A';
            }


            $(document).ready(function() {
                // fetch the file
                var geometry = {{ geometry | tojson }};
                var directions = {{ directions | tojson }};

                var marker;
                var currentDirectionIndex = 0;
                var currentStepIndex = 0;
                const map = findLeafletMap();

                function showStep() {

                    var direction = directions[currentDirectionIndex];
                    var step = direction.steps[currentStepIndex];
                    const icon = mapDirectionToFontAwesome(step.instruction);

                    var markerIcon = L.divIcon({
                        html: `<img src="${icons[icon]}">`,
                        iconSize: [40, 40],
                        iconAnchor: [20, 20],
                        className: 'direction-marker',
                    });

                    if (step.way_points && step.way_points.length > 0) {
                        if (marker) {
                            map.removeLayer(marker);
                        }

                        var firstPoint = step.way_points[0]; // Get the first point
                        var lastPoint = step.way_points[step.way_points.length - 1]; // Get the last point
                        var lat_lng = geometry[firstPoint]; // Get the lat/lng of the first point
                        map.flyTo([lat_lng[1], lat_lng[0]], 19); // Pan the map to the first point

                        marker = L.marker([lat_lng[1], lat_lng[0]], {
                            icon: markerIcon,
                            className: 'direction-marker-icon',
                        }).addTo(map);
                    }

                    $('#directionsContainer').html(`
                        <div class="align-center route-info">
                            <div class='instruction' style="">
                                <img src="${icons[icon]}" style="width: 50px; height: 50px; margin-right: 10px; margin-top: auto; margin-bottom: auto;">
                                ${step.instruction}
                            </div>
                            <p style='font-size: 1rem'>Store ${currentDirectionIndex + 1}: ${direction.distance} mi (total)</p>
                            <p>Distance: ${step.distance} mi</p>
                            <p>Duration: ${secondsToHms(step.duration)}</p>
                        </div>
                    `);

                }


                function nextStep() {
                    var direction = directions[currentDirectionIndex];
                    if (currentStepIndex < direction.steps.length - 1) {
                        currentStepIndex++;
                        showStep();
                    } else if (currentDirectionIndex < directions.length - 1) {
                        currentDirectionIndex++;
                        currentStepIndex = 0;
                        showStep();
                    }
                }

                function prevStep() {
                    if (currentStepIndex > 0) {
                        currentStepIndex--;
                        showStep();
                    } else if (currentDirectionIndex > 0) {
                        currentDirectionIndex--;
                        currentStepIndex = directions[currentDirectionIndex].steps.length - 1;
                        showStep();
                    }
                }

                $('.next-step').click(nextStep);
                $('.prev-step').click(prevStep);

                // Initially show the first step of the first direction
                showStep();
            });"""
