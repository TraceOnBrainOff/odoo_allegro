#Do the logic in _process_products(), repurpose _fetch_image_urls_from_google() for sending the offer in Allegro's API,
#
import allegro_auth

import base64
import logging
from datetime import timedelta
import string
import json

import requests
from requests.exceptions import ConnectionError as RequestConnectionError

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductSendAllegroOfferWizard(models.TransientModel):
    _name = 'product.send.allegro.offer.wizard'
    _description = "Send catalogue related offers to Allegro based on the provided barcode."
    _session = requests.Session()
    _token = None

    @api.model
    def default_get(self, fields_list): #Should be OK
        # Check that the cron has not been deleted and raise an error if so
        ir_cron_send_allegro_offer = self.env.ref(
            'odoo_allegro.ir_cron_send_allegro_offer', raise_if_not_found=False
        )
        if not ir_cron_send_allegro_offer:
            raise UserError(_(
                "The scheduled action \"Allegro Offers: Send Offer to Allegro\" has "
                "been deleted. Please contact your administrator to have the action restored "
                "or to reinstall the module \"odoo_allegro\"."
            ))

        # Check that the cron is not already triggered and raise an error if so
        cron_triggers_count = self.env['ir.cron.trigger'].search_count(
            [('cron_id', '=', ir_cron_send_allegro_offer.id)]
        )
        if cron_triggers_count > 0:
            raise UserError(_(
                "A task to process products in the background is already running. Please try again"
                "later."
            ))

        # Check if API keys are set without retrieving the values to avoid leaking them
        ICP = self.env['ir.config_parameter']
        allegro_client_id_is_set = bool(ICP.get_param('allegro.application.id'))
        allegro_client_secret_is_set = bool(ICP.get_param('allegro.application.secret'))
        if not (allegro_client_id_is_set and allegro_client_secret_is_set):
            raise UserError(_(
                "The Client ID and Client Secret must be set in the General Settings."
            ))

        # Compute default values
        if self._context.get('active_model') == 'product.template':
            product_ids = self.env['product.template'].browse(
                self._context.get('active_ids')
            ).product_variant_ids
        else:
            product_ids = self.env['product.product'].browse(
                self._context.get('active_ids')
            )
        al_products_selected = len(product_ids)
        products_to_process = product_ids.filtered(lambda p: bool(p.barcode))
        al_products_to_process = len(products_to_process)
        al_products_unable_to_process = al_products_selected - al_products_to_process
        defaults = super().default_get(fields_list)
        defaults.update(
            products_to_process=products_to_process,
            al_products_selected=al_products_selected,
            al_products_to_process=al_products_to_process,
            al_products_unable_to_process=al_products_unable_to_process,
        )
        return defaults

    al_products_selected = fields.Integer(string="Number of selected products", readonly=True)
    products_to_process = fields.Many2many(
        comodel_name='product.product',
        help="The list of selected products that meet the criteria (have a barcode)",
    )
    al_products_to_process = fields.Integer(string="Number of products to process", readonly=True)
    al_products_unable_to_process = fields.Integer(
        string="Number of product unprocessable", readonly=True
    )

    def action_send_allegro_offer(self):
        """ Fetch the images of the first ten products and delegate the remaining to the cron.

        The first ten images are immediately fetched to improve the user experience. This way, they
        can immediately browse the processed products and be assured that the task is running well.
        Also, if any error occurs, it can be thrown to the user. Then, a cron job is triggered to be
        run as soon as possible, unless the daily request limit has been reached. In that case, the
        cron job is scheduled to run a day later.

        :return: A notification to inform the user about the outcome of the action
        :rtype: dict
        """
        self.products_to_process.send_allegro_offer_pending = True  # Flag products to process for the cron

        # Process the first 10 products immediately
        self._process_products(self._get_products_to_process(10))

        if self._get_products_to_process(1):  # Delegate remaining products to the cron
            # Check that the cron has not been deleted and raise an error if so
            ir_cron_send_allegro_offer = self.env.ref(
                'odoo_allegro.ir_cron_send_allegro_offer', raise_if_not_found=False
            )
            if not ir_cron_send_allegro_offer:
                raise UserError(_(
                    "The scheduled action \"Product Images: Get product images from Google\" has "
                    "been deleted. Please contact your administrator to have the action restored "
                    "or to reinstall the module \"odoo_allegro\"."
                ))

            # Check that the cron is not already triggered and create a new trigger if not
            cron_triggers_count = self.env['ir.cron.trigger'].search_count(
                [('cron_id', '=', ir_cron_send_allegro_offer.id)]
            )
            if cron_triggers_count == 0:
                self.with_context(automatically_triggered=False)._trigger_send_allegro_offers_cron()
            message = _(
                "Products are processed in the background."
            )
            warning_type = 'success'
        else:
            message = _(
                "Offers have been sent for %(product_count)s "
                "products.",
                product_count=len(self.products_to_process)
            )
            warning_type = 'success'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Allegro offers"),
                'type': warning_type,
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _cron_send_allegro_offer(self): #Seems OK
        """ Fetch images of a list of products using their barcode.

        This method is called from a cron job. If the daily request limit is reached, the cron job
        is scheduled to run again a day later.

        :return: None
        """
        # Retrieve 100 products at a time to limit the run time and avoid reaching Google's default
        # rate limit.
        self._process_products(self._get_products_to_process(100))
        if self._get_products_to_process(1):
            self.with_context(automatically_triggered=True)._trigger_send_allegro_offers_cron(
                fields.Datetime.now() + timedelta(minutes=1.0)
            )

    def _get_products_to_process(self, limit=10000): #Seems OK
        """ Get the products that need to be processed and meet the criteria.

        The criteria are to have a barcode and no image. If `products_to_process` is not populated,
        the DB is searched to find matching product records.

        :param int limit: The maximum number of records to return, defaulting to 10000 to match
                          Google's API default rate limit
        :return: The products that meet the criteria
        :rtype: recordset of `product.product`
        """
        products_to_process = self.products_to_process or self.env['product.product'].search(
            [('send_allegro_offer_pending', '=', True)], limit=limit
        )
        return products_to_process.filtered(
            # p.send_allegro_offer_pending needed for self.products_to_process's records that might already
            # have been processed but not yet removed from the list when called from
            # action_fetch_image.
            lambda p: p.barcode and p.send_allegro_offer_pending
        )[:limit]  # Apply the limit after the filter with self.products_to_process for more results

    def _process_products(self, products_to_process):
        if not products_to_process:
            return 0

        al_service_unavailable_codes = 0
        al_timeouts = 0
        for product in products_to_process:
            # Fetch image URLs and handle eventual errors
            try:
                response = self._send_offer_from_barcode_to_allegro(product.barcode)
                if response.status_code == requests.codes.forbidden:
                    raise UserError(_(
                        f"Forbidden. Reason: {string(response.json())}"
                    ))
                elif response.status_code == requests.codes.service_unavailable:
                    al_service_unavailable_codes += 1
                    if al_service_unavailable_codes <= 3:  # Temporary loss of service
                        continue  # Let the image of this product be fetched by the next cron run

                    # The service has not responded more  han 3 times, stop trying for now and wait
                    # for the next cron run.
                    self.with_context(automatically_triggered=True)._trigger_send_allegro_offers_cron(
                        fields.Datetime.now() + timedelta(minutes=5.0)
                    )
                    _logger.warning(
                        "received too many service_unavailable responses. delegating remaining "
                        "offers to next cron run."
                    )
                    break
                elif response.status_code == requests.codes.too_many_requests:
                    self.with_context(automatically_triggered=True)._trigger_send_allegro_offers_cron(
                        fields.Datetime.now() + timedelta(minutes=1.0)
                    )
                    _logger.warning(
                        "offer limit reached. schedulring rest for cron."
                    )
                    break
                elif response.status_code == requests.codes.bad_request:
                    raise UserError(_(
                        f"Bad Request. Reason: {string(response.json())}"
                    ))
                elif response.status_code == requests.codes.unauthorized:
                    raise UserError(_(
                        f"Unauthorized. Reason: {string(response.json())}"
                    ))
                elif response.status_code == 422: #Unprocessable Entity
                    raise UserError(_(
                        f"Unprocessable Entity. Reason: {string(response.json())}"
                    ))
            except (RequestConnectionError):
                al_timeouts += 1
                if al_timeouts <= 3:  # Temporary loss of service
                    continue  # Let the image of this product be fetched by the next cron run

                # The service has not responded more  han 3 times, stop trying for now and wait for
                # the next cron run.
                self.with_context(automatically_triggered=True)._trigger_send_allegro_offers_cron(
                    fields.Datetime.now() + timedelta(minutes=5.0)
                )
                _logger.warning(
                    "encountered too many timeouts. delegating remaining offers to next cron run."
                )
                break

            # Fetch image and handle possible error
            response_content = response.json()
            if response.status_code==201:
                pass
            elif response.status_code==202:
                pass
            else:
                pass

            product.send_allegro_offer_pending = False
            self.env.cr.commit()  # Commit every image in case the cron is killed

    def _send_offer_from_barcode_to_allegro(self, barcode):
        """Allegro's rate limit is 9000 per minute, if you exceed that, it'll lock your client ID for a minute
        If this happens they return 429 Too Many Requests. 

        """
        """ Fetch the first 10 image URLs from the Google Custom Search API.

        :param string barcode: A product's barcode
        :return: A response or None
        :rtype: Response
        """
        if not barcode:
            return
        ICP = self.env['ir.config_parameter']
        CLIENT_ID = ICP.get_param('allegro.application.id').strip()
        CLIENT_SECRET = ICP.get_param('allegro.application.secret').strip()
        access_token = allegro_auth.token_check(ICP, CLIENT_ID, CLIENT_SECRET)
        return self._session.get(
            url='https://api.allegro.pl/sale/product-offers',
            headers={
                'authorization': f'Bearer {access_token}',
                'accept': 'application/vnd.allegro.public.v1+json',
                'content-type': 'application/vnd.allegro.public.v1+json',
            },
            params={
                'productSet': [{
                    'product': {
                        "id": barcode,
                        "idType": "GTIN"
                    }
                }],
                "sellingMode": {
                    "price": {
                        "amount": 1,
                        "currency": "PLN"
                    }
                },
                "stock": {
                    "available": 1
                },
                "publication": {
                    "status": "INACTIVE"
                }
            }
        )

    def _trigger_send_allegro_offers_cron(self, at=None): #OK
        """ Create a trigger for the con `ir_cron_send_allegro_offer`.

        By default the cron is scheduled to be executed as soon as possible but
        the optional `at` argument may be given to delay the execution later
        with a precision down to 1 minute.

        :param Optional[datetime.datetime] at:
            When to execute the cron, at one moments in time instead of as soon as possible.
        """
        self.env.ref('odoo_allegro.ir_cron_send_allegro_offer')._trigger(at)
        # If two `ir_cron_send_allegro_offer` are triggered automatically, and the first one is not
        # committed, the constrains will return a ValidationError and roll back to the last commit,
        # leaving no `ir_cron_send_allegro_offer` in the schedule.
        self.env.cr.commit()
